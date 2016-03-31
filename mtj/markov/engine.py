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

from .utils import pair
from .utils import unique_merge
from .word import chain_to_words
from .word import normalize

# XXX fix this (by moving code depending on that below)
from .model.normal import Chain
from .model.normal import Fragment
from .model.normal import Word
from .model.normal import IndexWordChain

from .model import Markov

logger = getLogger(__name__)
_f_id = '_f_id'
_word = '_word'


class HandledError(Exception):
    """
    Ignorable error.
    """


class Engine(object):

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 ):
        self.db_src = db_src

        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance

    def initialize(self, **kw):
        if hasattr(self, 'engine'):
            logger.info('Engine already initialized')
            return

        self.engine = create_engine(self.db_src, **kw)
        Markov.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def session(self):
        return self._sessions()

    def _merge_sentence(self, sentence, session):
        source = sentence.split()
        if len(source) < self.min_sentence_length:
            return []
        words = [''] + source + ['']

        try:
            words = [unique_merge(session, Word, word=word) for word in words]
        except DataError as e:
            # most likely due to invalid data types.
            session.rollback()
            logger.exception('Failed to learn this sentence: %s', sentence)
            raise HandledError
        else:
            return words
        return []

    def _merge_words(self, words, session):
        fragments = [unique_merge(
            session, Fragment, l_word=lw, r_word=rw) for lw, rw in pair(words)]
        return fragments

    def _learn(self, sentence, session):
        words = self._merge_sentence(sentence, session)
        fragments = self._merge_words(words, session)
        chains = [Chain(*v) for v in pair(fragments)]

        # Since the chains are guaranteed to be unique from the rest
        # already in the table, we can just track this here.
        table = set()
        for chain in chains:
            for word in chain_to_words(chain):
                nword = normalize(word.word)
                if nword == word.word:
                    table.add((chain, word))
                    continue
                # Ensure the normalized word is merged properly.
                table.add((chain, unique_merge(session, Word, word=nword)))

        idx = [IndexWordChain(chain, word) for chain, word in table]
        session.add_all(chains)
        session.add_all(idx)

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

    def generate(self, word, default=None):
        normalize(word)
        session = self.session()
        idx = session.query(IndexWordChain).join(Word).filter(
            Word.word == normalize(word)).all()

        if not idx:
            if default is not None:
                return default
            raise KeyError('no such word in chains')

        # pick a chain
        target = random.choice(idx).chain

        lhs = self.follow_chain(target, 'rl', session)
        c = [i.word for i in chain_to_words(target)]
        rhs = self.follow_chain(target, 'lr', session)

        result = lhs + c + rhs
        return ' '.join(result).strip()
