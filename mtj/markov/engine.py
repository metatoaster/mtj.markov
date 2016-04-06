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
from . import base

logger = getLogger(__name__)


class Engine(base.Engine):
    """
    Description of the engine class.
    """

    def initialize(self, db_src='sqlite://',
                   min_sentence_length=1,
                   max_chain_distance=50,
                   model_module=normal,
                   **kw):
        if hasattr(self, 'engine'):
            logger.info('Engine already initialized')
            return

        self.db_src = db_src
        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.model_module = model_module

        self.engine = create_engine(self.db_src, **kw)
        # XXX document how this part came to be, why state_graph.model
        self.state_graph.model.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def get_session(self):
        """
        Used by StateGraph.

        Currently defined to be an SQLAlchemy session object, but it
        should be generalized.
        """

        return self._sessions()

    def generate(self, *a, **kw):
        """
        Generate a MarkovChain based on the StateGraph
        """

        return self.state_graph.generate(*a, **kw)

    def learn(self, sentence):
        """
        Learn a sentence.
        """

        chains = self.state_graph.merge(sentence)
        return chains
