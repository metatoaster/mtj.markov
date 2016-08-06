import unittest

from sqlalchemy.orm.session import Session

from mtj.markov.graph import sentence
from mtj.markov.graph.sentence import SentenceGraph

from mtj.markov.testing import XorShift128


class SentenceTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = SentenceGraph()
        self.engine.initialize()
        sentence.random, self.original_random = XorShift128(), sentence.random

    def tearDown(self):
        sentence.random = self.original_random

    def skip_random(self, n=1):
        # For skipping over unfavorable generated numbers.
        for i in range(n):
            sentence.random()

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
        self.assertEqual(s.query(engine.Word).count(), 13)
        self.assertEqual(s.query(engine.Fragment).count(), 13)
        self.assertEqual(s.query(engine.IndexWordFragment).count(), 13)
        self.assertEqual(s.query(engine.IndexWordFragment).join(
            engine.Word).filter(engine.Word.word == 'you').count(), 2)
        self.assertEqual(s.query(engine.IndexWordFragment).join(
            engine.Word).filter(engine.Word.word == 'abyss').count(), 2)

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

    def test_generate_not_unendingly_circular(self):
        engine = self.engine
        p = 'circular logic works because circular logic'
        engine.learn(p)
        self.skip_random(2)
        self.assertEqual(
            engine.generate('logic'),
            'circular logic works because circular logic')
        # I had previously neglected this case, and this turns out to
        # make the above best case again less common.
        self.assertEqual(engine.generate('logic'), 'circular logic')

    def test_sentence_postlearn_hook(self):
        _values = []
        engine = self.engine

        def hook(*a):
            _values.extend(a)

        engine.register_sentence_postlearn_hook(hook)
        engine.learn('this should be hooked')
        sentence, session = _values
        self.assertFalse(sentence is None)
        self.assertTrue(isinstance(session, Session))
