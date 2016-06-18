# -*- coding: utf-8 -*-
from logging import getLogger
from time import time
from random import random

from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.exc import SQLAlchemyError

from .utils import unique_merge
from .utils import nchain
from .word import normalize
# from ..exc import HandledError

from .model import base
from .model import sentence

logger = getLogger(__name__)


class SentenceGraph(base.StateGraph):
    """
    The graph of sentences.
    """

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 normalize=normalize,
                 **kw):
        self.model = declarative_base(name='SentenceGraph')
        self.db_src = db_src
        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.normalize = normalize
        self.sentence_postlearn_hooks = []

    def initialize(self, **kw):
        self.engine = create_engine(self.db_src, **kw)

        # manually doing the mixin here because sqlalchemy doesn't seem
        # to have any way to mix different Bases together to make new
        # ones to maintain separate identities.

        for clsname in sentence.__all__:
            basecls = getattr(sentence, clsname)
            setattr(self, clsname, type(clsname, (basecls, self.model), {}))

        self.model.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def register_sentence_postlearn_hook(self, hook):
        """
        Register a sentence hook, which should be functions that accept
        the final sentence object (ORM) that was created and the current
        session object.  Intended use case is to allow the addition of
        related data/metadata related to the sentence into the backend.
        """

        self.sentence_postlearn_hooks.append(hook)

    def _gen_word_dict(self, words, session):
        """
        A dedicated method to generate a word dictionary that maps all
        input words (plus their normalized form) into the actual objects
        that are present inside the db.  If not they will be merged.

        Returns a dictionary that maps all words to be used for fragment
        generation.
        """

        # grab all of them with a single in statement.
        results = self.lookup_words_by_words(
            (set([normalize(w) for w in words] + words)),
            session)

        def merge(word):
            if word in results:
                return
            # hopefully these are unique.
            # results[word] = unique_merge(session, self.Word, word=word)
            results[word] = session.merge(self.Word(word=word))

        for word in words:
            merge(word)
            merge(self.normalize(word))

        return results

    def postlearn_hooks(self, sentence, session):
        # subclass can extend this.
        for hook in self.sentence_postlearn_hooks:
            hook(sentence, session)

    def _merge_states(self, words, timestamp=None, session=None):
        word_map = self._gen_word_dict(words, session)

        fragments = []
        indexes = []
        sentence = self.Sentence(timestamp)

        for chain in nchain(3, words):
            fragment = self.Fragment(sentence, *(word_map[c] for c in chain))
            fragments.append(fragment)
            nword = word_map[self.normalize(chain[1])]
            indexes.append(self.IndexWordFragment(nword, fragment))
        session.add(sentence)
        session.add_all(fragments)
        session.add_all(indexes)

        self.postlearn_hooks(sentence, session)

        return fragments

    def _learn(self, sentence, timestamp=None, session=None):
        if session is None:
            # XXX might be a hook within the StateGraph that is decoupled
            # from the SQLAlchemy engine.
            session = self._sessions()

        # source words
        source = sentence.split()
        if len(source) < self.min_sentence_length:
            return []
        words = [''] + source + ['']
        self._merge_states(words, timestamp=timestamp, session=session)

    def learn(self, sentence):
        try:
            session = self._sessions()
            fragments = self._learn(sentence, session=session)
        # Originally planned for handling individual word errors, but
        # given this is only triggered for more strict RDBMS and also
        # that the exception is only raised on commit, skip for now.
        # except HandledError as e:
        #     logger.error('Failed to learn sentence: %s', sentence)
        except SQLAlchemyError as e:
            logger.exception(
                'SQLAlchemy Error while learning: %s', sentence)
        except Exception as e:
            logger.exception('Unexpected error')
        else:
            session.commit()
            # These fragments (i.e. its id) can be used for association
            # with metadata.
            return fragments
        return []

    def lookup_words_by_ids(self, word_ids, session=None):
        """
        Return all words associated with the list of word_ids
        """

        if session is None:
            session = self._sessions()

        return dict(session.query(self.Word.id, self.Word.word).filter(
            self.Word.id.in_(word_ids)).all())

    def lookup_words_by_words(self, words, session=None):
        """
        Return all Words associated with the list of words
        """

        if session is None:
            session = self._sessions()

        return {w.word: w for w in session.query(self.Word).filter(
            self.Word.word.in_(words)).all()}

    def pick_state_transition(self, word, session):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        # XXX note pick_state_transition
        query = lambda p: session.query(p).select_from(
            self.IndexWordFragment).join(self.Word).filter(
            self.Word.word == self.normalize(word))

        count = query(func.count()).one()[0]

        if not count:
            raise KeyError('no such word in chains')

        fragment = query(self.IndexWordFragment).offset(
            int(random() * count)).first()
        return fragment.fragment

    def _query_chain(self, fragment, s_word_id, t_word_id, session):
        # self.Fragment.word_id points to a joiner, skip the second cond
        # which is the source restriction, so that words like "and" can
        # be treated as a standalone 1-order word.

        query = lambda p: session.query(p).select_from(self.Fragment).filter(
            (self.Fragment.word_id == getattr(fragment, t_word_id)) &
            (getattr(self.Fragment, s_word_id) == fragment.word_id))
        count = query(func.count()).one()[0]
        if not count:
            return None
        return query(self.Fragment).offset(int(random() * count)).first()

    def follow_chain(self, fragment, direction, session=None):
        """
        Follow the fragments for the list of word ids that will make a
        markov chain.

        direction, either
        - 'lr', left to right
        - 'rl', right to left
        """

        if session is None:  # pragma: no cover
            session = self._sessions()

        # split direction to target and source.
        s, t = direction
        _word_id = '_word_id'
        # build identifiers
        s_word_id, t_word_id = s + _word_id, t + _word_id

        result = []
        for c in range(self.max_chain_distance):
            fragment = self._query_chain(
                fragment, s_word_id, t_word_id, session)
            if not fragment:
                break
            result.append(getattr(fragment, t_word_id))

        if t == 'l':  # if target is towards left, reverse
            return list(reversed(result))
        return result

    def generate(self, word, default=None):
        # XXX different from parent definition.
        # XXX might be a hook within the StateGraph that is decoupled
        # from the SQLAlchemy engine.
        session = self._sessions()

        try:
            entry_point = self.pick_state_transition(word, session)
        except KeyError:
            if default is not None:
                return default
            raise

        lhs = self.follow_chain(entry_point, 'rl', session)
        c = list(entry_point.list_states())
        rhs = self.follow_chain(entry_point, 'lr', session)

        word_ids = lhs + c + rhs
        words = self.lookup_words_by_ids(word_ids, session)
        return ' '.join(words[word_id] for word_id in word_ids).strip()