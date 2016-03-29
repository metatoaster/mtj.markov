# -*- coding: utf-8 -*-
import unittest

from mtj.markov.utils import pair


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
