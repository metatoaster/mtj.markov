# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.orm import backref
from sqlalchemy.sql import func
from sqlalchemy.sql import select
from sqlalchemy.schema import MetaData
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Table
from sqlalchemy.schema import Column
from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declarative_base

Markov = declarative_base()


class Word(Markov):
    __tablename__ = 'word'

    id = Column(Integer(), primary_key=True, nullable=False)
    word = Column(String(length=255), nullable=False, index=True, unique=True)

    def __init__(self, word):
        self.word = word


class Fragment(Markov):
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


class Chain(Markov):
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
