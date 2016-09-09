from random import random
from sqlalchemy import func

from .sentence import SentenceGraph
from ..model import xmpp


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

    def pick_entry_point(self, data, session):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        # TODO verify that data is a word
        word = data.get('word')

        # XXX note pick_state_transition
        # XXX the condtion need to link to sentence AND xmpp stuff
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

        # ditto, the linkage is here, too.
        query = lambda p: session.query(p).select_from(self.Fragment).filter(
            (self.Fragment.word_id == getattr(fragment, t_word_id)) &
            (getattr(self.Fragment, s_word_id) == fragment.word_id))
        count = query(func.count()).one()[0]
        if not count:
            return None
        return query(self.Fragment).offset(int(random() * count)).first()
