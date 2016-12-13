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

from ..utils import unique_merge
from ..utils import nchain
from ..word import normalize
# from ..exc import HandledError

from ..model import sentence
from . import base

logger = getLogger(__name__)


class SentenceGraph(base.SqliteStateGraph):
    """
    The graph of sentences.
    """

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 normalize=normalize,
                 **kw):
        super(SentenceGraph, self).__init__(db_src, **kw)

        # XXX constants set somewhere not here.
        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.normalize = normalize

    def initialize(self, modules=None, **kw):
        local_modules = [sentence]
        if modules:
            # should probably append.
            local_modules.extend(modules)

        super(SentenceGraph, self).initialize(local_modules, **kw)

        # XXX assigning the autocreated classes in parent to here
        self.IndexWordFragment = self.classes['IndexWordFragment']
        self.Fragment = self.classes['Fragment']
        # self.Sentence = self.classes['Sentence']
        self.Word = self.classes['Word']

    def pick_word(self, session=None):
        if session is None:  # pragma: no cover
            session = self._sessions()

        query = lambda p: session.query(p).select_from(self.Word).filter(
            self.Word.word != '')
        count = query(func.count()).one()[0]

        if not count:
            raise KeyError('no words in graph')

        return self.normalize(
            query(self.Word.word).offset(int(random() * count)).first()[0])

    def pick_entry_point(self, data, session):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        # TODO verify that data is a word
        word = data.get('word')

        if not word:
            word = self.pick_word(session)

        query = lambda p: session.query(p).select_from(
            self.IndexWordFragment).join(self.Word).filter(
                self.Word.word == self.normalize(word))

        count = query(func.count()).one()[0]

        if not count:
            raise KeyError('no such word in chains')

        index = query(self.IndexWordFragment).offset(
            int(random() * count)).first()
        return index.fragment

    def _query_chain(self, data, fragment, s_word_id, t_word_id, session):
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

    def follow_chain(self, data, fragment, direction, session=None):
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
                data, fragment, s_word_id, t_word_id, session)
            if not fragment:
                break
            result.append(getattr(fragment, t_word_id))

        if t == 'l':  # if target is towards left, reverse
            return list(reversed(result))
        return result

    def _generate(self, data, default=None):
        result = super(SentenceGraph, self)._generate(data)
        return ' '.join(w.word for w in result).strip()
