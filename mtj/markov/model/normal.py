# -*- coding: utf-8 -*-
import random

from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Column
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import DataError

from ..utils import unique_merge
from ..utils import pair
from ..word import normalize
from . import base

Base = declarative_base(name='MarkovNormal')


class Word(base.State, Base):
    __tablename__ = 'word'

    id = Column(Integer(), primary_key=True, nullable=False)
    word = Column(String(length=255), nullable=False, index=True, unique=True)

    def __init__(self, word):
        self.word = word


class Fragment(Base):
    __tablename__ = 'fragment'

    id = Column('id', Integer(), primary_key=True, nullable=False)
    # left/right word id
    l_w_id = Column(Integer(), ForeignKey('word.id'), nullable=False)
    r_w_id = Column(Integer(), ForeignKey('word.id'), nullable=False)

    lr = UniqueConstraint(l_w_id, r_w_id)

    l_word = relationship('Word', foreign_keys=l_w_id)
    r_word = relationship('Word', foreign_keys=r_w_id)

    def __init__(self, l_word, r_word):
        self.l_word = l_word
        self.r_word = r_word


class Chain(base.StateTransition, Base):
    __tablename__ = 'chain'

    id = Column(Integer(), primary_key=True, nullable=False)
    # left/right fragment id
    l_f_id = Column(Integer(), ForeignKey('fragment.id'), nullable=False)
    r_f_id = Column(Integer(), ForeignKey('fragment.id'), nullable=False)

    l_fragment = relationship('Fragment', foreign_keys=l_f_id)
    r_fragment = relationship('Fragment', foreign_keys=r_f_id)

    def __init__(self, l_fragment, r_fragment):
        self.l_fragment = l_fragment
        self.r_fragment = r_fragment

    def to_words(self):
        # return all words within the chain.
        return (
            self.l_fragment.l_word,
            self.l_fragment.r_word,
            self.r_fragment.r_word,
        )


class IndexWordChain(Base):
    """
    Look up word to chain.  Reason for this seemingly redundant table is
    solely due to word allomorphs, i.e. plurals, or words with attached
    punctuation marks within the indexed word/fragment (which this does
    not currently handle).
    """

    __tablename__ = 'idx_word_chain'

    id = Column(Integer(), primary_key=True, nullable=False)
    word_id = Column(
        Integer(), ForeignKey('word.id'), index=True, nullable=False)
    chain_id = Column(
        Integer(), ForeignKey('chain.id'), index=True, nullable=False)

    word = relationship('Word', foreign_keys=word_id)
    chain = relationship('Chain', foreign_keys=chain_id)

    wc = UniqueConstraint(word_id, chain_id)

    def __init__(self, chain, word):
        self.chain = chain
        self.word = word


class StateGraph(base.StateGraph):

    def _merge_words(self, words, session):
        try:
            words = [unique_merge(session, Word, word=word) for word in words]
        except DataError as e:
            # most likely due to invalid data types.
            session.rollback()
            logger.exception('Failed to learn this sentence: %s', sentence)
            raise HandledError
        else:
            return words
        return []

    def _merge_fragments(self, words, session):
        fragments = [unique_merge(
            session, Fragment, l_word=lw, r_word=rw) for lw, rw in pair(words)]
        return fragments

    def _merge_all(self, words, session):
        words = self._merge_words(words, session)
        fragments = self._merge_fragments(words, session)
        chains = [Chain(*v) for v in pair(fragments)]

        # Since the chains are guaranteed to be unique from the rest
        # already in the table, we can just track this here.
        table = set()
        for chain in chains:
            for word in chain.to_words():
                nword = normalize(word.word)
                if nword == word.word:
                    table.add((chain, word))
                    continue
                # Ensure the normalized word is merged properly.
                table.add((chain, unique_merge(session, Word, word=nword)))

        idx = [IndexWordChain(chain, word) for chain, word in table]
        session.add_all(chains)
        session.add_all(idx)

    def _pick_entry_point(self, word, session):
        idx = session.query(IndexWordChain).join(Word).filter(
            Word.word == normalize(word)).all()

        if not idx:
            raise KeyError('no such word in chains')

        return random.choice(idx).chain
