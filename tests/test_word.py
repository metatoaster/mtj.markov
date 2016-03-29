# -*- coding: utf-8 -*-
import unittest

from mtj.markov.word import normalize


class NormalTestCase(unittest.TestCase):

    def test_normalized(self):
        self.assertEqual(normalize('hello'), 'hello')
        self.assertEqual(normalize('hello.'), 'hello')
        self.assertEqual(normalize('"hello,'), 'hello')
        self.assertEqual(normalize('"Hello,'), 'hello')
        self.assertEqual(normalize('"Hello...'), 'hello')

    def test_middle_saved(self):
        self.assertEqual(normalize('vO.Ov'), 'vO.Ov')

    def test_ignored(self):
        self.assertEqual(normalize('...'), '...')
        self.assertEqual(normalize(':)'), ':)')
        self.assertEqual(normalize('HeLlO'), 'HeLlO')
        self.assertEqual(normalize('CamelCase'), 'CamelCase')
        self.assertEqual(normalize('CamelBack'), 'CamelBack')
        self.assertEqual(normalize('BOOM'), 'BOOM')
        # heh.
        self.assertEqual(normalize('__init__'), '__init__')

    def test_mixed(self):
        self.assertEqual(normalize('...boo'), 'boo')
        self.assertEqual(normalize('hello:)'), 'hello')
        self.assertEqual(normalize('...HeLlO'), 'HeLlO')
        self.assertEqual(normalize('CamelCase:'), 'CamelCase')
        self.assertEqual(normalize('-CamelBack'), 'CamelBack')
        self.assertEqual(normalize('"BOOM"'), 'BOOM')
