# -*- coding: utf-8 -*-
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr

from . import base

__all__ = [
    'JID', 'Muc', 'Nickname', 'XMPPLog',
    'Loader',
]


class JID(base.Value):
    """
    The Jabber identifier for XMPP.  The bare JID is used to track the
    muc name and the users that were referenced, so who said what can be
    tracked.
    """

    __tablename__ = 'xmpp_jid'

    id = Column(Integer(), primary_key=True, nullable=False)
    value = Column(String(length=255), nullable=False, index=True, unique=True)


class Muc(base.Value):
    """
    The XMPP muc (multi-user chatroom) identifier.  While same as JID,
    it really should be treated as a distinct type to uniquely identify
    where the sentence was originally source.
    """

    __tablename__ = 'xmpp_muc'

    id = Column(Integer(), primary_key=True, nullable=False)
    value = Column(String(length=255), nullable=False, index=True, unique=True)


class Nickname(base.Value):
    """
    The nicknames used by the user when the message was logged.  This is
    derived from the resource portion of the JID of a MUC.  End-users
    will generally find this a lot easier to use.
    """

    __tablename__ = 'xmpp_nickname'

    id = Column(Integer(), primary_key=True, nullable=False)
    value = Column(String(length=255), nullable=False, index=True, unique=True)


class XMPPLog(base.Index):
    """
    Describes an XMPP sentence.
    """

    __tablename__ = 'xmpp_log'

    # columns

    id = Column(Integer(), primary_key=True, nullable=False)

    @declared_attr
    def sentence_id(cls):
        return Column(
            Integer(), ForeignKey('sentence.id'), nullable=False)

    @declared_attr
    def muc_id(cls):
        return Column(
            Integer(), ForeignKey('xmpp_muc.id'), nullable=False)

    @declared_attr
    def jid_id(cls):
        return Column(
            Integer(), ForeignKey('xmpp_jid.id'), nullable=False)

    @declared_attr
    def nickname_id(cls):
        return Column(
            Integer(), ForeignKey('xmpp_nickname.id'), nullable=False)

    # relationships

    @declared_attr
    def sentence(cls):
        return relationship('Sentence', foreign_keys=cls.sentence_id)

    @declared_attr
    def muc(cls):
        return relationship('Muc', foreign_keys=cls.muc_id)

    @declared_attr
    def jid(cls):
        return relationship('JID', foreign_keys=cls.jid_id)

    @declared_attr
    def nickname(cls):
        return relationship('Nickname', foreign_keys=cls.nickname_id)

    def __init__(self, sentence, muc, jid, nickname):
        self.sentence = sentence
        self.muc = muc
        self.jid = jid
        self.nickname = nickname


def lookup_words_by_words(words, session, Word):
    """
    Return all Words associated with the list of words
    """

    return {w.word: w for w in session.query(Word).filter(
        Word.word.in_(words)).all()}


class Loader(base.Loader):

    def __init__(self, graph):
        self.graph = graph
        self.min_sentence_length = graph.min_sentence_length
        self.normalize = graph.normalize

    # TODO document that any missing arguments with the exact names of
    # the classes defined that are missing will result in sql errors,
    # as they will no longer be the one that understand the protocol.

    def __call__(self, session, raw, datum,
                 JID=None, Muc=None, Nickname=None, XMPPLog=None,
                 **classes):
        """
        Loads things into the graph.
        """

        jid = JID.unique_merge(session, raw['jid'])
        muc = Muc.unique_merge(session, raw['muc'])
        nickname = Nickname.unique_merge(session, raw['nick'])

        log = XMPPLog(sentence=datum, muc=muc, jid=jid, nickname=nickname)
        session.merge(log)
