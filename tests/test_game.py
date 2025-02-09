import os
import sys

sys.path.append(os.getcwd())

import unittest

from components.Logger import Logger
from components.Player import Player
from Game import Game


class TestGame(unittest.TestCase):

    def strategy(self, state):
        return "f", -1

    def setUp(self):
        self.strategy_name = "alwaysfold"
        self.player1 = Player("1", 1000, self.strategy_name, self.strategy)
        self.player2 = Player("2", 1000, self.strategy_name, self.strategy)

        self.players = [self.player1, self.player2]

        self.logger = Logger(log_hands=False, strategies=[player.strategy_name for player in self.players], number_of_hands=2, simul=True)

        self.game = Game(self.players, self.logger, 2, simul=True)

    def test_sub_play(self):
        """
        Tests the sub_play method.\n
        Should check if the sub_play method returns 0 when game ended else 1.
        """

        testPlayers1 = [
            Player("1", 0, self.strategy_name, self.strategy),
            Player("2", 1000, self.strategy_name, self.strategy),
        ]

        testPlayers2 = [
            Player("1", 1000, self.strategy_name, self.strategy),
            Player("2", 1000, self.strategy_name, self.strategy),
        ]

        testGame = Game(testPlayers1, self.logger, 2, simul=True)
        self.assertEqual(testGame.sub_play(10), 0)

        testGame = Game(testPlayers2, self.logger, 2, simul=True)
        self.assertEqual(testGame.sub_play(10), 1)

    def test_player_bet(self):
        """
        Tests whether the player_bet function working or not.
        """

        testGame = Game(self.players, self.logger, 2, simul=True)

        returnValue = testGame.player_bet(self.player1, self.player1.bankroll + 100)
        self.assertEqual(returnValue, False)

        pot = testGame.pot + self.player1.bankroll - 100
        returnValue = testGame.player_bet(self.player1, self.player1.bankroll - 100)
        self.assertEqual(returnValue, None)

        self.assertEqual(testGame.pot, pot)
