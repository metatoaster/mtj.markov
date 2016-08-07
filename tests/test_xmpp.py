import unittest

from sqlalchemy.orm.session import Session

from mtj.markov.graph import sentence as graph_sentence
from mtj.markov.graph.sentence import SentenceGraph

from mtj.markov.model import sentence
from mtj.markov.model import xmpp

from mtj.markov.testing import XorShift128


class SentenceTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = SentenceGraph()
        self.engine.initialize([xmpp])
        graph_sentence.random, self.original_random = (
            XorShift128(), graph_sentence.random)

    def tearDown(self):
        graph_sentence.random = self.original_random

    def skip_random(self, n=1):
        # For skipping over unfavorable generated numbers.
        for i in range(n):
            graph_sentence.random()

    def test_basic_generate(self):
        engine = self.engine
        engine.learn({
            sentence.Loader: 'how are you doing',
            xmpp.Loader: {
                'muc': 'room@chat.example.com',
                'jid': 'user@example.com',
                'nick': 'A Test User',
            }
        })

        chain = engine.generate('you')
        self.assertEqual(chain, 'how are you doing')

        s = self.engine._sessions()
        self.assertEqual(
            s.query(engine.classes['Nickname']).first().value, 'A Test User')
        self.assertEqual(
            s.query(engine.classes['XMPPLog']).first().jid.value,
            'user@example.com')

    def test_multiple_generate(self):
        engine = self.engine
        engine.learn({
            sentence.Loader: 'how are you doing',
            xmpp.Loader: {
                'muc': 'room@chat.example.com',
                'jid': 'user1@example.com',
                'nick': 'User 1',
            }
        })

        engine.learn({
            sentence.Loader: 'I am fine, thank you.',
            xmpp.Loader: {
                'muc': 'room@chat.example.com',
                'jid': 'user2@example.com',
                'nick': 'User 2',
            }
        })

        chain = engine.generate('you')

        s = self.engine._sessions()
        self.assertEqual(
            sorted(i.value for i in s.query(engine.classes['JID']).all()),
            ['user1@example.com', 'user2@example.com'],
        )
        self.assertEqual(
            sorted(i.value for i in s.query(engine.classes['Muc']).all()),
            ['room@chat.example.com'],
        )
        self.assertEqual(s.query(engine.classes['XMPPLog']).count(), 2)
