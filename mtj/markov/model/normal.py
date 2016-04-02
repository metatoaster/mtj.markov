# -*- coding: utf-8 -*-
import random

from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
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
from . import normal

_f_id = '_f_id'
_word = '_word'

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


class HandledError(Exception):
    """
    Ignorable error.
    """


class Engine(StateGraph):

    def __init__(self, db_src='sqlite://',
                 min_sentence_length=1,
                 max_chain_distance=50,
                 model_module=normal,
                 ):
        self.db_src = db_src

        self.min_sentence_length = min_sentence_length
        # maximum distance from starting chain for output.
        self.max_chain_distance = max_chain_distance
        self.model_module = model_module

    def initialize(self, **kw):
        if hasattr(self, 'engine'):
            logger.info('Engine already initialized')
            return

        self.engine = create_engine(self.db_src, **kw)
        self.model_module.Base.metadata.create_all(self.engine)
        self._sessions = scoped_session(sessionmaker(bind=self.engine))

    def session(self):
        return self._sessions()

    def _learn(self, sentence, session):
        source = sentence.split()
        if len(source) < self.min_sentence_length:
            return []
        words = [''] + source + ['']
        self._merge_all(words, session)

    def learn(self, sentence):
        session = self.session()
        try:
            chains = self._learn(sentence, session)
        except HandledError as e:
            # Should have been dealt with.
            pass
        except SQLAlchemyError as e:
            logger.exception(
                'SQLAlchemy Error while learning: %s', sentence)
        except Exception as e:
            logger.exception('Unexpected error')
        else:
            # These chains (i.e. its id) can be used for association
            # with metadata.
            session.commit()
            return chains
        return []

    def follow_chain(self, target, direction, session):
        """
        Follow the chain

        direction, either
        - 'lr', left to right
        - 'rl', right to left
        """

        # split direction to target and source.
        s, t = direction
        # build identifiers
        s_f_id, t_f_id = s + _f_id, t + _f_id
        tw = t + _word

        target = getattr(target, t_f_id)

        result = []
        for c in range(self.max_chain_distance):
            choices = session.query(getattr(Chain, t_f_id)).filter(
                getattr(Chain, s_f_id) == target).all()
            if not choices:
                break

            target = random.choice(choices)[0]
            word = session.query(Word.word).select_from(Fragment).join(
                getattr(Fragment, tw)).filter(
                Fragment.id==target).first()[0]
            result.append(word)

        if t == 'l':  # if target is towards left, reverse
            return list(reversed(result))
        return result

    def _pick_entry_point(self, word, session):
        idx = session.query(IndexWordChain).join(Word).filter(
            Word.word == normalize(word)).all()

        if not idx:
            raise KeyError('no such word in chains')

        return random.choice(idx).chain

    def generate(self, word, default=None):
        normalize(word)
        session = self.session()

        try:
            entry_point = self._pick_entry_point(word, session)
        except KeyError:
            if default is not None:
                return default
            raise

        lhs = self.follow_chain(entry_point, 'rl', session)
        c = [i.word for i in entry_point.to_words()]
        rhs = self.follow_chain(entry_point, 'lr', session)

        result = lhs + c + rhs
        return ' '.join(result).strip()
