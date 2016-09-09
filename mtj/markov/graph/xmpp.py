from logging import getLogger
from random import random
from sqlalchemy import func

from .sentence import SentenceGraph
from ..model import xmpp

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

        # XXX ignoring word
        query = lambda p: session.query(p).select_from(
            self.Fragment).join(
                self.XMPPLog,
                self.XMPPLog.sentence_id == self.Fragment.sentence_id
            ).join(self.JID).filter(self.JID.value == jid)

        count = query(func.count()).one()[0]

        if not count:
            raise KeyError('failed to find fragments for jid <%s>', jid)

        fragment = query(self.Fragment).offset(
            int(random() * count)).first()
        logger.debug('picked fragment_id %d', fragment.id)
        return fragment

    def _query_chain(self, data, fragment, s_word_id, t_word_id, session):
        jid = data.get('jid')
        if not jid:
            # See pick_entry_point
            return super(XMPPGraph, self)._query_chain(
                data, fragment, s_word_id, t_word_id, session)

        # self.Fragment.word_id points to a joiner, skip the second cond
        # which is the source restriction, so that words like "and" can
        # be treated as a standalone 1-order word.

        # ditto, the linkage is here, too.
        query = lambda p: session.query(p).select_from(self.Fragment).join(
                self.XMPPLog,
                self.XMPPLog.sentence_id == self.Fragment.sentence_id
            ).join(self.JID).filter(
                (self.JID.value == jid) &
                (self.Fragment.word_id == getattr(fragment, t_word_id)) &
                (getattr(self.Fragment, s_word_id) == fragment.word_id)
            )
        count = query(func.count()).one()[0]
        if not count:
            return None
        return query(self.Fragment).offset(int(random() * count)).first()
