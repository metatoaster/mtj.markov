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

from .model import Chain
from .model import Fragment
from .model import Markov
from .model import Word
from .model import IndexWordChain

logger = getLogger(__name__)


class HandledError(Exception):
    """
    Ignorable error.
    """


class Engine(object):

    _fragment_id = ('l_fragment', 'r_fragment')
    _word_id = ('l_word', 'r_word')

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=3,
                 max_chain_distance=50,
                 ):
        self.db_src = db_src
        # Need a minimum of 3 words per sentence to build a chain.
        # If single/double word sentences are desired, the code will
        # need to support generation of empty placeholder words.
        self.min_sentence_length = max(3, min_sentence_length)

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
        words = sentence.split()
        # if we want to support single or double word sentences, pad the
        # above to at least 3 items (i.e. append 1 or 2 empty strings).
        # no idea what the effects may be.
        if len(words) < self.min_sentence_length:
            return []

        try:
            words = [unique_merge(
                session, Word, word=word) for word in words]
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

    def learn(self, sentence):
        session = self.session()
        try:
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
            try:
                session.add_all(chains)
                session.add_all(idx)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.exception(
                    'SQLAlchemy Error while learning: %s', sentence)
        except HandledError as e:
            # Should have been dealt with.
            pass
        except Exception as e:
            session.rollback()
            logger.exception('Unexpected error')
        else:
            # These chains (i.e. its id) can be used for association
            # with metadata.
            return chains
        return []

    def follow_chain(self, target, direction, session):
        # Alternatively, apply the equation -(i+1), where i are the
        # indexes for self._fragment_id

        # find LHS
        # session.query(Chain).filter(
        #     Chain.r_fragment == target.chain.l_fragment)[0]
        # # find RHS
        # session.query(Chain).filter(
        #     Chain.l_fragment == target.chain.r_fragment)[0]

        if direction:  # towards right
            sf, tf = self._fragment_id
            sw, tw = self._word_id
        else:  # towards left
            tf, sf = self._fragment_id
            tw, sw = self._word_id

        result = []
        for c in range(self.max_chain_distance):
            result.append(getattr(getattr(target, tf), tw).word)
            choices = session.query(Chain).filter(
                getattr(Chain, sf) == getattr(target, tf)).all()
            if not choices:
                break
            target = random.choice(choices)

        if not direction:
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

        lhs = self.follow_chain(target, False, session)
        # should be same as chain.r_fragment.l_word.word
        c = [target.l_fragment.r_word.word]
        rhs = self.follow_chain(target, True, session)

        result = lhs + c + rhs
        return ' '.join(result)
