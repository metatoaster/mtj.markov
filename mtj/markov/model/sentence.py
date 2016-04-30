# -*- coding: utf-8 -*-
from logging import getLogger
from time import time
from random import random

from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.exc import DataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError

from ..utils import unique_merge
from ..utils import nchain
from ..word import normalize
# from ..exc import HandledError
from . import base

Base = declarative_base(name='Text')
logger = getLogger(__name__)


class Sentence(Base):
    __tablename__ = 'sentence'

    # metadata attaches to this.
    id = Column(Integer(), primary_key=True, nullable=False)
    # This is the most basic extended attribute.
    timestamp = Column(Integer(), nullable=False)

    def __init__(self, timestamp=None):
        if timestamp is None:
            timestamp = int(time())
        self.timestamp = timestamp


class Word(base.State, Base):
    __tablename__ = 'word'

    id = Column(Integer(), primary_key=True, nullable=False)
    word = Column(String(length=255), nullable=False, index=True, unique=True)

    def __init__(self, word):
        self.word = word


class Fragment(base.StateTransition, Base):
    """
    A fragment of a sentence, 3 word states = 2-order markov.
    """

    __tablename__ = 'fragment'

    id = Column(Integer(), primary_key=True, nullable=False)
    sentence_id = Column(Integer(), ForeignKey('sentence.id'), nullable=False)
    l_word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)
    word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)
    r_word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)

    sentence = relationship('Sentence', foreign_keys=sentence_id)
    l_word = relationship('Word', foreign_keys=l_word_id)
    word = relationship('Word', foreign_keys=word_id)
    r_word = relationship('Word', foreign_keys=r_word_id)

    # This is deferred to IndexWordFragment
    # idx_word = Index('word_id', 'word_id')
    idx_l_word = Index('idx_l_word', word_id, r_word_id)
    idx_r_word = Index('idx_r_word', l_word_id, word_id)
    # TODO figure out how to get all fragments associated with this
    # fragment at either directions.

    def __init__(self, sentence, l_word, word, r_word):
        self.sentence = sentence
        self.l_word = l_word
        self.word = word
        self.r_word = r_word

    def list_states(self):
        # return the raw identifiers.
        return (
            self.l_word_id,
            self.word_id,
            self.r_word_id,
        )


class IndexWordFragment(Base):
    """
    Look up word to fragment.  Reason for this seemingly redundant table
    is solely due to word allomorphs, i.e. plurals, capitalization or
    other characters that should be removed.

    The words to be indexed should be the ones that form the order, i.e.
    the edge words (l_ or r_ prefixed) should be omitted.
    """

    __tablename__ = 'idx_word_fragment'

    # XXX probably don't need id as the primary key
    id = Column(Integer(), primary_key=True, nullable=False)
    word_id = Column(
        Integer(), ForeignKey('word.id'), index=True, nullable=False)
    fragment_id = Column(
        Integer(), ForeignKey('fragment.id'), index=True, nullable=False)

    word = relationship('Word', foreign_keys=word_id)
    fragment = relationship('Fragment', foreign_keys=fragment_id)

    wc = UniqueConstraint(word_id, fragment_id)

    def __init__(self, word, fragment):
        self.word = word
        self.fragment = fragment


class WordGraph(base.StateGraph):
    """
    The graph of words.
    """

    model = Base

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 normalize=normalize,
                 **kw):
        self.db_src = db_src
        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.normalize = normalize
        self.sentence_postlearn_hooks = []

    def initialize(self, **kw):
        self.engine = create_engine(self.db_src, **kw)
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
            # results[word] = unique_merge(session, Word, word=word)
            results[word] = session.merge(Word(word=word))

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
        sentence = Sentence(timestamp)

        for chain in nchain(3, words):
            fragment = Fragment(sentence, *(word_map[c] for c in chain))
            fragments.append(fragment)
            nword = word_map[self.normalize(chain[1])]
            indexes.append(IndexWordFragment(nword, fragment))
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

        return dict(session.query(Word.id, Word.word).filter(
            Word.id.in_(word_ids)).all())

    def lookup_words_by_words(self, words, session=None):
        """
        Return all Words associated with the list of words
        """

        if session is None:
            session = self._sessions()

        return {w.word: w for w in session.query(Word).filter(
            Word.word.in_(words)).all()}

    def pick_state_transition(self, word, session):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        # XXX note pick_state_transition
        query = lambda p: session.query(p).select_from(
            IndexWordFragment).join(Word).filter(
            Word.word == self.normalize(word))

        count = query(func.count()).one()[0]

        if not count:
            raise KeyError('no such word in chains')

        fragment = query(IndexWordFragment).offset(
            int(random() * count)).first()
        return fragment.fragment

    def _query_chain(self, fragment, s_word_id, t_word_id, session):
        query = lambda p: session.query(p).select_from(Fragment).filter(
            (Fragment.word_id == getattr(fragment, t_word_id)) &
            (getattr(Fragment, s_word_id) == fragment.word_id))
        count = query(func.count()).one()[0]
        if not count:
            return None
        return query(Fragment).offset(int(random() * count)).first()

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
