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
from sqlalchemy.ext.declarative import declared_attr

from . import base

__all__ = ['Sentence', 'Word', 'Fragment', 'IndexWordFragment']


class Sentence(object):
    __tablename__ = 'sentence'

    # metadata attaches to this.
    id = Column(Integer(), primary_key=True, nullable=False)
    # This is the most basic extended attribute.
    timestamp = Column(Integer(), nullable=False)

    def __init__(self, timestamp=None):
        if timestamp is None:
            timestamp = int(time())
        self.timestamp = timestamp


class Word(base.State):
    __tablename__ = 'word'

    id = Column(Integer(), primary_key=True, nullable=False)
    word = Column(String(length=255), nullable=False, index=True, unique=True)

    def __init__(self, word):
        self.word = word


class Fragment(base.StateTransition):
    """
    A fragment of a sentence, 3 word states = 2-order markov.
    """

    __tablename__ = 'fragment'

    id = Column(Integer(), primary_key=True, nullable=False)
    @declared_attr
    def sentence_id(cls):
        return Column(Integer(), ForeignKey('sentence.id'), nullable=False)

    @declared_attr
    def l_word_id(cls):
        return Column(Integer(), ForeignKey('word.id'), nullable=False)

    @declared_attr
    def word_id(cls):
        return Column(Integer(), ForeignKey('word.id'), nullable=False)

    @declared_attr
    def r_word_id(cls):
        return Column(Integer(), ForeignKey('word.id'), nullable=False)

    @declared_attr
    def sentence(cls):
        return relationship('Sentence', foreign_keys=cls.sentence_id)

    @declared_attr
    def l_word(cls):
        return relationship('Word', foreign_keys=cls.l_word_id)

    @declared_attr
    def word(cls):
        return relationship('Word', foreign_keys=cls.word_id)

    @declared_attr
    def r_word(cls):
        return relationship('Word', foreign_keys=cls.r_word_id)


    # This is deferred to IndexWordFragment
    # idx_word = Index('word_id', 'word_id')
    @declared_attr
    def idx_l_word(cls):
        return Index('idx_l_word', cls.word_id, cls.r_word_id)

    @declared_attr
    def idx_r_word(cls):
        return Index('idx_r_word', cls.l_word_id, cls.word_id)

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


class IndexWordFragment(object):
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

    @declared_attr
    def word_id(cls):
        return Column(Integer(), ForeignKey('word.id'), index=True, nullable=False)

    @declared_attr
    def fragment_id(cls):
        return Column(Integer(), ForeignKey('fragment.id'), index=True, nullable=False)

    @declared_attr
    def word(cls):
        return relationship('Word', foreign_keys=cls.word_id)

    @declared_attr
    def fragment(cls):
        return relationship('Fragment', foreign_keys=cls.fragment_id)


    @declared_attr
    def wc(cls):
        return UniqueConstraint(cls.word_id, cls.fragment_id)

    def __init__(self, word, fragment):
        self.word = word
        self.fragment = fragment
