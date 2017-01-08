from logging import getLogger
from random import random
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy import Index
from sqlalchemy import MetaData
from sqlalchemy import Table

from .sentence import SentenceGraph
from ..model import xmpp
from ..model.sentence import FragmentBase

logger = getLogger(__name__)


class XMPPGraph(SentenceGraph):
    """
    The graph of sentences.
    """

    def initialize(self, modules=None, **kw):
        local_modules = [xmpp]
        if modules:
            # should probably append.
            local_modules.extend(modules)

        super(XMPPGraph, self).initialize(local_modules, **kw)

        # XXX assigning the autocreated classes in parent to here
        self.JID = self.classes['JID']
        self.Muc = self.classes['Muc']
        self.Nickname = self.classes['Nickname']
        self.XMPPLog = self.classes['XMPPLog']

        # construct ORM temporary classes after real stuff are done
        self.FragmentTemp = type('FragmentTemp', (FragmentBase, self.model), {
            '__tablename__': 'fragment_xmpp_temp',
            '__table_args__': {'prefixes': ['TEMP']},
        })

    def pick_entry_point(self, data, session):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        jid = data.get('jid')
        if not jid:
            # XXX what about nickname and muc??
            # only rely on jid for the mean time, figure out the metrics
            # for mapping nickname + muc to jid
            return super(XMPPGraph, self).pick_entry_point(data, session)

        insq = session.query(self.Fragment).select_from(
            self.Fragment).join(
                self.XMPPLog,
                self.XMPPLog.sentence_id == self.Fragment.sentence_id
            ).join(self.JID).filter(self.JID.value == jid)

        # create temporary table
        # checkfirst as some implementations keep them around...
        self.FragmentTemp.__table__.create(
            bind=session.connection(), checkfirst=True)

        # directly poking at the table.
        # TODO figure out ORM equivalent...
        session.execute(self.FragmentTemp.__table__.insert().from_select(
            self.Fragment.__table__.columns, insq))

        count = session.query(self.FragmentTemp).count()

        if not count:
            raise KeyError('failed to find fragments for jid <%s>', jid)

        fragment = session.query(self.FragmentTemp).offset(
            int(random() * count)).first()
        logger.debug('picked fragment_id %d', fragment.id)

        # bind the Fragment table reference to the session object
        session.Fragment = self.FragmentTemp
        return fragment
