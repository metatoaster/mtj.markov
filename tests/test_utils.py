# -*- coding: utf-8 -*-
import unittest

from mtj.markov.utils import nchain
from mtj.markov.utils import pair
# unique_merge is tested under normal usage.


class PairTestCase(unittest.TestCase):

    def test_pair_empty(self):
        results = list(pair([]))
        self.assertEqual(results, [])

    def test_pair_single_item(self):
        results = list(pair(['a']))
        self.assertEqual(results, [])

    def test_pair_two_items(self):
        results = list(pair(['a', 'b']))
        self.assertEqual(results, [('a', 'b')])

    def test_pair_multiple_items(self):
        results = list(pair('abcd'))
        self.assertEqual(results, [('a', 'b'), ('b', 'c'), ('c', 'd')])


class NchainTestCase(unittest.TestCase):

    def test_nchain_empty(self):
        results = list(nchain(2, []))
        self.assertEqual(results, [])
        results = list(nchain(3, []))
        self.assertEqual(results, [])

    def test_nchain_single_item(self):
        results = list(nchain(2, ['a']))
        self.assertEqual(results, [])
        results = list(nchain(3, ['a']))
        self.assertEqual(results, [])

    def test_3chain_two_items(self):
        results = list(nchain(3, ['a', 'b']))
        self.assertEqual(results, [])

    def test_3chain_three_items(self):
        results = list(nchain(3, ['a', 'b', 'c']))
        self.assertEqual(results, [('a', 'b', 'c')])

    def test_3chain_four_items(self):
        results = list(nchain(3, ['a', 'b', 'c', 'd']))
        self.assertEqual(results, [('a', 'b', 'c'), ('b', 'c', 'd')])

    def test_3chain_items(self):
        results = list(nchain(3, ['a', 'b', 'c', 'd', 'e', 'f']))
        self.assertEqual(results, [
            ('a', 'b', 'c'),
            ('b', 'c', 'd'),
            ('c', 'd', 'e'),
            ('d', 'e', 'f'),
        ])

    def test_4chain_three_items(self):
        results = list(nchain(4, ['a', 'b', 'c']))
        self.assertEqual(results, [])

    def test_3chain_four_items(self):
        results = list(nchain(4, ['a', 'b', 'c', 'd']))
        self.assertEqual(results, [('a', 'b', 'c', 'd')])
