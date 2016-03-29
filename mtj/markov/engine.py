# -*- coding: utf-8 -*-
from logging import getLogger

from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError

from .utils import pair
from .utils import unique_merge

from .model import Chain
from .model import Fragment
from .model import Markov
from .model import Word

logger = getLogger(__name__)


class HandledError(Exception):
    """
    Ignorable error.
    """


class Engine(object):

    def __init__(self, db_src='sqlite://', min_sentence_length=3):
        self.db_src = db_src
        # Need a minimum of 3 words per sentence to build a chain.
        # If single/double word sentences are desired, the code will
        # need to support generation of empty placeholder words.
        self.min_sentence_length = max(3, min_sentence_length)

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

            try:
                session.add_all(chains)
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

    def generate(self, word, default=None):
        if default is not None:
            return default
        raise KeyError('no such word in chains')
