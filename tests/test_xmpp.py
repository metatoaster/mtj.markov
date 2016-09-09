import unittest

from random import Random
from sqlalchemy.orm.session import Session

from mtj.markov.graph import sentence as graph_sentence
from mtj.markov.graph import xmpp as graph_xmpp
from mtj.markov.graph.xmpp import XMPPGraph

from mtj.markov.model import sentence
from mtj.markov.model import xmpp

from mtj.markov.testing.mocks import stub_module_random


class XMPPTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = XMPPGraph()
        self.engine.initialize()
        stub_module_random(self, graph_sentence)
        stub_module_random(self, graph_xmpp)

    def tearDown(self):
        pass

    def skip_random(self, n=1):
        # For skipping over unfavorable generated numbers.
        for i in range(n):
            self._random_mod.random()

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

    def test_data_specific_generation(self):
        def split_text(text):
            return [s.strip() for s in text.splitlines()]

        user1_text = split_text("""
            Today is a bright fine day.
            He was not a bright person.
            I wish he was not so skinny.
            She will be a bright star in the dark skies.
        """)

        user2_text = split_text("""
            Today is a bad day.
            Yesterday there was a bright fine explosion.
            I am too tired to deal with this.
            She will not be forgotten.
        """)

        data = (
            ('user1@example.com', 'User 1', user1_text),
            ('user2@example.com', 'User 2', user2_text),
        )

        engine = self.engine

        for jid, nick, text in data:
            for s in text:
                engine.learn({
                    sentence.Loader: s,
                    xmpp.Loader: {
                        'muc': 'room@chat.example.com',
                        'jid': jid,
                        'nick': nick,
                    }
                })

        today = engine.generate('Today')
        self.assertEqual(today, 'Today is a bright person.')
        # combining things both users said.
        chain = engine.generate('bright')
        self.assertEqual(chain, 'Yesterday there was a bright person.')

        # user1_bright = engine.generate('bright', jid='user1@example.com')

        # s = self.engine._sessions()
        # self.assertEqual(
        #     sorted(i.value for i in s.query(engine.classes['JID']).all()),
        #     ['user1@example.com', 'user2@example.com'],
        # )
        # self.assertEqual(
        #     sorted(i.value for i in s.query(engine.classes['Muc']).all()),
        #     ['room@chat.example.com'],
        # )
        # self.assertEqual(s.query(engine.classes['XMPPLog']).count(), 2)
