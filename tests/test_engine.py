import unittest

from mtj.markov.engine import Engine
from mtj.markov.model import Chain
from mtj.markov.model import Fragment
from mtj.markov.model import IndexWordChain
from mtj.markov.model import Word


class EngineTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = Engine()
        self.engine.initialize()

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
        self.assertEqual(s.query(Word).count(), 4)
        self.assertEqual(s.query(Fragment).count(), 3)
        self.assertEqual(s.query(Chain).count(), 2)

        # no addition word or fragments
        engine.learn('how are you')
        self.assertEqual(s.query(Word).count(), 4)
        self.assertEqual(s.query(Fragment).count(), 3)
        # but we get a new chain
        self.assertEqual(s.query(Chain).count(), 3)

    def test_learn_same_word(self):
        engine = self.engine
        s = engine.session()

        engine.learn('to be or not to be')
        self.assertEqual(s.query(Word).count(), 4)
        self.assertEqual(s.query(Fragment).count(), 4)
        self.assertEqual(s.query(Chain).count(), 4)

        engine.learn('dust to dust')
        self.assertEqual(s.query(Word).count(), 5)
        self.assertEqual(s.query(Fragment).count(), 6)
        self.assertEqual(s.query(Chain).count(), 5)

        engine.learn('badger badger badger')
        self.assertEqual(s.query(Word).count(), 6)
        self.assertEqual(s.query(Fragment).count(), 7)
        self.assertEqual(s.query(Chain).count(), 6)

    def test_multi_learn(self):
        engine = self.engine
        engine.learn('how is this a problem')
        engine.learn('what is a carrier')

        s = engine.session()
        self.assertEqual(s.query(Word).count(), 7)
        self.assertEqual(s.query(Fragment).count(), 7)
        self.assertEqual(s.query(Chain).count(), 5)

    def test_learn_normalize_index(self):
        engine = self.engine
        s = engine.session()

        engine.learn(
            'if you gaze long into an abyss, the abyss also gazes into you.')
        self.assertEqual(s.query(Word).count(), 12)  # dup: long
        self.assertEqual(s.query(Fragment).count(), 12)
        self.assertEqual(s.query(Chain).count(), 11)
        self.assertEqual(s.query(IndexWordChain).count(), 32)
        self.assertEqual(s.query(IndexWordChain).join(Word).filter(
            Word.word == 'you').count(), 3)
        self.assertEqual(s.query(IndexWordChain).join(Word).filter(
            Word.word == 'abyss').count(), 5)

    def test_basic_generate(self):
        engine = self.engine
        engine.learn('how are you doing')

        chain = engine.generate('you')
        self.assertEqual(chain, 'how are you doing')

    def test_generate_sentence_clean(self):
        engine = self.engine
        engine.learn('how is this a problem')
        engine.learn('what is a carrier')

        # generate 100 chains
        chains = set(engine.generate('a', default='') for i in range(100))

        # only two unique sentences should be generated, cannot generate
        # e.g. 'how is this a carrier' ('this a carrier' not a chain)
        self.assertTrue(0 < len(chains) <= 2)
