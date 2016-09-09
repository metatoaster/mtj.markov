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

# from ..exc import HandledError

from ..model import base

logger = getLogger(__name__)


class SqliteStateGraph(base.StateGraph):
    """
    Generic sqlite state graph implementation
    """

    def __init__(self, db_src='sqlite://', **kw):
        self.model = declarative_base(name=type(self).__name__)
        self.classes = {}
        self.db_src = db_src
        self.loaders = []

    def initialize(self, modules, **kw):
        self.engine = create_engine(self.db_src, **kw)

        # manually doing the mixin here because sqlalchemy doesn't seem
        # to have any way to mix different Bases together to make new
        # ones to maintain separate identities.

        for module in modules:
            for clsname in module.__all__:
                basecls = getattr(module, clsname)
                if issubclass(basecls, base.Node):
                    # Do the actual mixin and assign its instance here.
                    # TODO maybe automagically determine which are the
                    # key classes so that they can contain stuff that do
                    # the actual learning?
                    # XXX what about naming conflicts?
                    cls = self.classes[clsname] = type(
                        clsname,
                        (basecls, self.model),
                        {}
                    )
                    # XXX again, should check for dupes...
                    if issubclass(cls, base.State):
                        self.State = cls
                    elif issubclass(cls, base.Datum):
                        self.Datum = cls
                elif issubclass(basecls, base.Loader):
                    self.loaders.append(basecls(self))

        self.model.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def learn(self, table):
        try:
            session = self._sessions()
        except Exception:
            logger.exception('Unexpected error')
            return

        try:
            datum = self.Datum()
            for loader in self.loaders:
                raw = table[type(loader)]
                session.add(datum)
                loader(session, raw, datum, **self.classes)
        except SQLAlchemyError as e:
            logger.exception(
                'SQLAlchemy Error while learning: %s', datum)
            session.rollback()
        except Exception as e:
            logger.exception('Unexpected error')
            session.rollback()
        else:
            session.commit()

    def lookup_states_by_ids(self, state_ids, session=None):
        """
        Return all words associated with the list of word_ids
        """

        if session is None:
            session = self._sessions()

        return {state.id: state for state in (session.query(self.State).filter(
            self.State.id.in_(state_ids)).all())}

    def pick_entry_point(self, data, session):
        """
        Return an entry point based on data.

        Current implementation specific.
        """

        raise NotImplementedError

    def follow_chain(self, data, fragment, direction, session=None):
        """
        Follow the fragments for the list of word ids that will make a
        markov chain.

        direction, either
        - 'lr', left to right
        - 'rl', right to left
        """

        raise NotImplementedError

    def _generate(self, data):
        # XXX different from parent definition.
        session = self._sessions()
        entry_point = self.pick_entry_point(data, session)

        lhs = self.follow_chain(data, entry_point, 'rl', session)
        c = list(entry_point.list_states())
        rhs = self.follow_chain(data, entry_point, 'lr', session)

        state_ids = lhs + c + rhs
        states = self.lookup_states_by_ids(state_ids, session)
        return (states[state_id] for state_id in state_ids)

    def generate(self, data, default=NotImplemented):
        # XXX different from parent definition.
        try:
            return self._generate(data)
        except KeyError:
            if default is NotImplemented:
                raise
            return default
