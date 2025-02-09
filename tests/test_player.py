import os
import sys

sys.path.append(os.getcwd())

import unittest

from components.Player import Player


class TestPlayer(unittest.TestCase):

    # Setting up the basics of test
    def setUp(self):
        self.test_player = Player(1, 1000)

    # Tests whether the package_state method giving proper information
    def test_package_state(self):
        state = self.test_player.package_state()

        self.assertDictEqual(
            {
                "id": 1,
                "hand": [],
                "bankroll": 1000,
                "betamt": 0,
                "ingame": 1,
                "strategy": "",
            },
            state,
        )

    # Tests whether player's are receiving proper cards
    def test_receive_card(self):
        self.test_player.receive_card("As")
        self.test_player.receive_card("Ks")

        self.assertDictEqual(
            {
                "id": 1,
                "hand": ["As", "Ks"],
                "bankroll": 1000,
                "betamt": 0,
                "ingame": 1,
                "strategy": "",
            },
            self.test_player.package_state(),
        )

    # Checks whether bet method works or not
    def test_bet(self):
        prevState = self.test_player.package_state()
        self.test_player.bet(100)

        prevState["bankroll"] -= 100
        prevState["betamt"] += 100

        self.assertDictEqual(prevState, self.test_player.package_state())

    # Tests if bankroll cannot be negative by the bet method
    def test_bankroll_positive(self):
        prevState = self.test_player.package_state()

        betAmt = prevState["bankroll"] + 100

        returnValue = self.test_player.bet(betAmt)

        self.assertFalse(returnValue)
        self.assertDictEqual(prevState, self.test_player.package_state())

    # Tests flush method actually resets or not
    def test_flush(self):
        prevState = self.test_player.package_state()

        self.test_player.flush()

        updatedState = prevState
        updatedState["hand"] = []
        updatedState["ingame"] = 1
        updatedState["betamt"] = 0

        self.assertDictEqual(updatedState, self.test_player.package_state())

    # Tests whether duplicates are added or not
    def test_no_duplicates(self):
        self.test_player.receive_card("As")

        with self.assertRaises(Exception) as context:
            self.test_player.receive_card("As")
