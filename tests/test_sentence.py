import unittest

from mtj.markov.model.sentence import Sentence
from mtj.markov.model.sentence import Fragment
from mtj.markov.model.sentence import Word
from mtj.markov.model.sentence import WordGraph
from mtj.markov.model.sentence import IndexWordFragment


class SentenceTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = WordGraph()
        self.engine.initialize()

    def test_lookup_words_by_ids(self):
        engine = self.engine
        engine.learn('hello this beautiful world.')

        words = engine.lookup_words_by_ids([4, 5, 6, 7])

        # empty string plus "world", or normalized form of "world.".
        self.assertEqual(sorted(words.keys()), [4, 5, 6])

    def test_lookup_words_by_words(self):
        engine = self.engine
        engine.learn('hello this beautiful world.')

        words = engine.lookup_words_by_words(
            ['hello', 'this', 'strange', 'world'])

        # `world.` should have been normalized to `world`.
        self.assertEqual(sorted(words.keys()), ['hello', 'this', 'world'])

    def test_learn_results(self):
        engine = self.engine
        s = self.engine._sessions()

        engine.learn(
            'if you gaze long into an abyss, the abyss also gazes into you.')
        self.assertEqual(s.query(Word).count(), 13)
        self.assertEqual(s.query(Fragment).count(), 13)
        self.assertEqual(s.query(IndexWordFragment).count(), 13)
        self.assertEqual(s.query(IndexWordFragment).join(Word).filter(
            Word.word == 'you').count(), 2)
        self.assertEqual(s.query(IndexWordFragment).join(Word).filter(
            Word.word == 'abyss').count(), 2)

    def test_learn_failure_sql(self):
        engine = self.engine
        # force a failure of some kind.
        s = self.engine._sessions()
        s.execute('DROP TABLE `word`')
        engine.learn('this cannot be learned.')

    def test_learn_failure_logic(self):
        engine = self.engine
        # force a programming error of some kind.
        del self.engine._sessions
        engine.learn('this cannot be learned.')

    def test_learn_raw(self):
        engine = self.engine
        session = self.engine._sessions()
        engine._learn('this cannot be learned.')
        session.commit()
        chain = engine.generate('this')
        self.assertEqual(chain, 'this cannot be learned.')

    def test_learn_restricted(self):
        engine = self.engine
        engine.min_sentence_length = 3
        result = engine.learn('hello world')
        self.assertEqual(len(result), 0)
        with self.assertRaises(KeyError):
            result = engine.generate('hi')

    def test_null_generate(self):
        engine = self.engine
        with self.assertRaises(KeyError):
            result = engine.generate('hi')

    def test_null_generate_default(self):
        engine = self.engine
        _marker = object()
        result = engine.generate('hi', _marker)
        self.assertIs(result, _marker)

    def test_basic_generate(self):
        engine = self.engine
        engine.learn('how are you doing')

        # both directions
        chain = engine.generate('you')
        self.assertEqual(chain, 'how are you doing')
        chain = engine.generate('doing')
        self.assertEqual(chain, 'how are you doing')

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
