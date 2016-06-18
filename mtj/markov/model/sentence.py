# -*- coding: utf-8 -*-
from time import time

from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declarative_base

from . import base

Base = declarative_base(name='Text')


class Sentence(Base):
    __tablename__ = 'sentence'

    # metadata attaches to this.
    id = Column(Integer(), primary_key=True, nullable=False)
    # This is the most basic extended attribute.
    timestamp = Column(Integer(), nullable=False)

    def __init__(self, timestamp=None):
        if timestamp is None:
            timestamp = int(time())
        self.timestamp = timestamp


class Word(base.State, Base):
    __tablename__ = 'word'

    id = Column(Integer(), primary_key=True, nullable=False)
    word = Column(String(length=255), nullable=False, index=True, unique=True)

    def __init__(self, word):
        self.word = word


class Fragment(base.StateTransition, Base):
    """
    A fragment of a sentence, 3 word states = 2-order markov.
    """

    __tablename__ = 'fragment'

    id = Column(Integer(), primary_key=True, nullable=False)
    sentence_id = Column(Integer(), ForeignKey('sentence.id'), nullable=False)
    l_word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)
    word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)
    r_word_id = Column(Integer(), ForeignKey('word.id'), nullable=False)

    sentence = relationship('Sentence', foreign_keys=sentence_id)
    l_word = relationship('Word', foreign_keys=l_word_id)
    word = relationship('Word', foreign_keys=word_id)
    r_word = relationship('Word', foreign_keys=r_word_id)

    # This is deferred to IndexWordFragment
    # idx_word = Index('word_id', 'word_id')
    idx_l_word = Index('idx_l_word', word_id, r_word_id)
    idx_r_word = Index('idx_r_word', l_word_id, word_id)
    # TODO figure out how to get all fragments associated with this
    # fragment at either directions.

    def __init__(self, sentence, l_word, word, r_word):
        self.sentence = sentence
        self.l_word = l_word
        self.word = word
        self.r_word = r_word

    def list_states(self):
        # return the raw identifiers.
        return (
            self.l_word_id,
            self.word_id,
            self.r_word_id,
        )


class IndexWordFragment(Base):
    """
    Look up word to fragment.  Reason for this seemingly redundant table
    is solely due to word allomorphs, i.e. plurals, capitalization or
    other characters that should be removed.

    The words to be indexed should be the ones that form the order, i.e.
    the edge words (l_ or r_ prefixed) should be omitted.
    """

    __tablename__ = 'idx_word_fragment'

    # XXX probably don't need id as the primary key
    id = Column(Integer(), primary_key=True, nullable=False)
    word_id = Column(
        Integer(), ForeignKey('word.id'), index=True, nullable=False)
    fragment_id = Column(
        Integer(), ForeignKey('fragment.id'), index=True, nullable=False)

    word = relationship('Word', foreign_keys=word_id)
    fragment = relationship('Fragment', foreign_keys=fragment_id)

    wc = UniqueConstraint(word_id, fragment_id)

    def __init__(self, word, fragment):
        self.word = word
        self.fragment = fragment
