import unittest

from mtj.markov.model.normal import Engine
from mtj.markov.model.normal import Chain
from mtj.markov.model.normal import Fragment
from mtj.markov.model.normal import IndexWordChain
from mtj.markov.model.normal import Word


class EngineLearnTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = Engine(min_sentence_length=3)
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

        # generate 100 chains
        chains = set(engine.generate('a', default='') for i in range(100))

        # only two unique sentences should be generated, cannot generate
        # e.g. 'how is this a carrier' ('this a carrier' not a chain)
        self.assertTrue(0 < len(chains) <= 2)

    def test_generate_terminate(self):
        engine = self.engine
        engine.learn('will start the engine tomorrow')
        engine.learn('the fire will start')
        chains = set(engine.generate('the', default='') for i in range(100))
        self.assertIn('the fire will start', chains)

    def test_generate_not_circular(self):
        engine = self.engine
        p = 'circular logic works because circular logic'
        engine.learn(p)
        # As the ends link up with each other, there is always a 50/50
        # chance that it will pick the other end when generating, i.e.
        # a 75% chance that two or more continuations will occur; work
        # around this by generating 10 chains for about 1 in a million
        # chance that the original sentence will be absent from output.
        # At least keep this until the random module gets mocked.
        chains = set(engine.generate('logic', default='') for i in range(10))
        self.assertIn(p, chains)
