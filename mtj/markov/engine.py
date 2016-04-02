# -*- coding: utf-8 -*-
from logging import getLogger
import random

from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError

from .word import normalize

from .model import normal

# XXX fix this (by moving code depending on that below)
from .model.normal import Chain
from .model.normal import Fragment
from .model.normal import Word
from .model.normal import IndexWordChain
from .model.normal import StateGraph

logger = getLogger(__name__)
_f_id = '_f_id'
_word = '_word'


class HandledError(Exception):
    """
    Ignorable error.
    """


class Engine(StateGraph):

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 model_module=normal,
                 ):
        self.db_src = db_src

        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.model_module = model_module

    def initialize(self, **kw):
        if hasattr(self, 'engine'):
            logger.info('Engine already initialized')
            return

        self.engine = create_engine(self.db_src, **kw)
        self.model_module.Base.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def session(self):
        return self._sessions()

    def _learn(self, sentence, session):
        source = sentence.split()
        if len(source) < self.min_sentence_length:
            return []
        words = [''] + source + ['']
        self._merge_all(words, session)

    def learn(self, sentence):
        session = self.session()
        try:
            chains = self._learn(sentence, session)
        except HandledError as e:
            # Should have been dealt with.
            pass
        except SQLAlchemyError as e:
            logger.exception(
                'SQLAlchemy Error while learning: %s', sentence)
        except Exception as e:
            logger.exception('Unexpected error')
        else:
            # These chains (i.e. its id) can be used for association
            # with metadata.
            session.commit()
            return chains
        return []

    def follow_chain(self, target, direction, session):
        """
        Follow the chain

        direction, either
        - 'lr', left to right
        - 'rl', right to left
        """

        # split direction to target and source.
        s, t = direction
        # build identifiers
        s_f_id, t_f_id = s + _f_id, t + _f_id
        tw = t + _word

        target = getattr(target, t_f_id)

        result = []
        for c in range(self.max_chain_distance):
            choices = session.query(getattr(Chain, t_f_id)).filter(
                getattr(Chain, s_f_id) == target).all()
            if not choices:
                break

            target = random.choice(choices)[0]
            word = session.query(Word.word).select_from(Fragment).join(
                getattr(Fragment, tw)).filter(
                Fragment.id==target).first()[0]
            result.append(word)

        if t == 'l':  # if target is towards left, reverse
            return list(reversed(result))
        return result

    def _pick_entry_point(self, word, session):
        idx = session.query(IndexWordChain).join(Word).filter(
            Word.word == normalize(word)).all()

        if not idx:
            raise KeyError('no such word in chains')

        return random.choice(idx).chain

    def generate(self, word, default=None):
        normalize(word)
        session = self.session()

        try:
            entry_point = self._pick_entry_point(word, session)
        except KeyError:
            if default is not None:
                return default
            raise

        lhs = self.follow_chain(entry_point, 'rl', session)
        c = [i.word for i in entry_point.to_words()]
        rhs = self.follow_chain(entry_point, 'lr', session)

        result = lhs + c + rhs
        return ' '.join(result).strip()
