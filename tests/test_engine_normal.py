import unittest

from mtj.markov.model import normal
from mtj.markov.model.normal import Engine
from mtj.markov.model.normal import Chain
from mtj.markov.model.normal import Fragment
from mtj.markov.model.normal import IndexWordChain
from mtj.markov.model.normal import Word

from mtj.markov.testing import XorShift128


class EngineLearnTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = Engine(min_sentence_length=3)
        self.engine.initialize()
        normal.random, self.original_random = XorShift128(), normal.random

    def tearDown(self):
        normal.random = self.original_random

    def test_empty(self):
        engine = self.engine
        with self.assertRaises(KeyError):
            engine.generate('you')

        chain = engine.generate('you', default='<default>')
        self.assertEqual(chain, '<default>')

    def test_cannot_learn_too_short(self):
        engine = self.engine
        engine.learn('')
        engine.learn('hello')
        engine.learn('hello world')
        s = engine.session()
        # All input were below minimum sentence length.
        self.assertEqual(s.query(Word).count(), 0)
        self.assertEqual(s.query(Fragment).count(), 0)
        self.assertEqual(s.query(Chain).count(), 0)

    def test_basic_learn(self):
        engine = self.engine
        engine.learn('how are you doing')
        s = engine.session()

        # verify insertion
        self.assertEqual(s.query(Word).count(), 5)
        self.assertEqual(s.query(Fragment).count(), 5)
        self.assertEqual(s.query(Chain).count(), 4)

        # no addition word or fragments
        engine.learn('how are you')
        self.assertEqual(s.query(Word).count(), 5)
        self.assertEqual(s.query(Fragment).count(), 6)
        # but we get a new chain
        self.assertEqual(s.query(Chain).count(), 7)

    def test_learn_same_word(self):
        engine = self.engine
        s = engine.session()

        engine.learn('to be or not to be')
        self.assertEqual(s.query(Word).count(), 5)
        self.assertEqual(s.query(Fragment).count(), 6)
        self.assertEqual(s.query(Chain).count(), 6)

        engine.learn('dust to dust')
        self.assertEqual(s.query(Word).count(), 6)
        self.assertEqual(s.query(Fragment).count(), 10)
        self.assertEqual(s.query(Chain).count(), 9)

        engine.learn('badger badger badger')
        self.assertEqual(s.query(Word).count(), 7)
        self.assertEqual(s.query(Fragment).count(), 13)
        self.assertEqual(s.query(Chain).count(), 12)

    def test_multi_learn(self):
        engine = self.engine
        engine.learn('how is this a problem')
        engine.learn('what is a carrier')

        s = engine.session()
        self.assertEqual(s.query(Word).count(), 8)
        self.assertEqual(s.query(Fragment).count(), 11)
        self.assertEqual(s.query(Chain).count(), 9)


class EngineUsageTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = Engine()
        self.engine.initialize()
        normal.random, self.original_random = XorShift128(), normal.random

    def tearDown(self):
        normal.random = self.original_random

    def skip_random(self, n=1):
        # For skipping over unfavorable generated numbers.
        for i in range(n):
            normal.random()

    def test_learn_normalize_index(self):
        engine = self.engine
        s = engine.session()

        engine.learn(
            'if you gaze long into an abyss, the abyss also gazes into you.')
        self.assertEqual(s.query(Word).count(), 13)  # dup: long
        self.assertEqual(s.query(Fragment).count(), 14)
        self.assertEqual(s.query(Chain).count(), 13)
        self.assertEqual(s.query(IndexWordChain).count(), 38)
        self.assertEqual(s.query(IndexWordChain).join(Word).filter(
            Word.word == 'you').count(), 5)
        self.assertEqual(s.query(IndexWordChain).join(Word).filter(
            Word.word == 'abyss').count(), 5)

    def test_basic_generate(self):
        engine = self.engine
        engine.learn('how are you doing')

        chain = engine.generate('you')
        self.assertEqual(chain, 'how are you doing')

        # XXX not used... figure out how.
        engine.learn('are you doing well')

    def test_basic_generate_long(self):
        engine = self.engine
        p = 'if you gaze long into an abyss, the abyss also gazes into you.'
        engine.learn(p)
        chain = engine.generate('an')
        self.assertEqual(chain, p)

    def test_generate_sentence_clean(self):
        engine = self.engine
        engine.learn('how is this a problem')
        engine.learn('what is a carrier')
        self.skip_random(8)

        self.assertEqual(engine.generate('a'), 'what is a carrier')
        self.assertEqual(engine.generate('a'), 'how is this a problem')

        # generate 100 chains to test that the two learned setences are
        # not actually connected at all (due to terminator).
        # e.g. 'how is this a carrier' ('this a carrier' not a chain)
        chains = set(engine.generate('a', default='') for i in range(100))
        self.assertTrue(0 < len(chains) <= 2)

    def test_generate_terminate(self):
        engine = self.engine
        engine.learn('will start the engine tomorrow')
        engine.learn('the fire will start')
        self.skip_random(14)
        self.assertEqual(
            engine.generate('the'), 'the fire will start')
        self.assertEqual(
            engine.generate('the'), 'the fire will start the engine tomorrow')
        self.assertEqual(
            engine.generate('the'), 'will start the engine tomorrow')

    def test_generate_not_circular(self):
        engine = self.engine
        p = 'circular logic works because circular logic'
        engine.learn(p)
        self.skip_random(4)
        self.assertEqual(
            engine.generate('logic'),
            'circular logic works because circular logic')
