# Unit tests for the utilities

import unittest

from poker_metrics.utils import *

test_state_0 = {
    "player": {
        "id": 1,
        "hand": ["5d", "6s"],
        "bankroll": 998,
        "betamt": 2,
        "ingame": 1,
    },
    "players": [],
    "call_value": 0,
    "players_playing": 5,
    "community_cards": [],
    "pot": 9,
    "round": 0,
    "max_bet": 998,
}

test_state_1 = {
    "player": {
        "id": 1,
        "hand": ["5d", "6s"],
        "bankroll": 998,
        "betamt": 2,
        "ingame": 1,
    },
    "players": [],
    "call_value": 0,
    "players_playing": 5,
    "community_cards": ["5d", "8d", "4s"],
    "pot": 9,
    "round": 1,
    "max_bet": 998,
}

test_state_2 = {
    "player": {
        "id": 1,
        "hand": ["9s", "5s"],
        "bankroll": 2000,
        "betamt": 0,
        "ingame": 1,
    },
    "players": [],
    "call_value": 40,
    "players_playing": 5,
    "community_cards": [],
    "pot": 9,
    "round": 0,
    "max_bet": 998,
}

test_state_3 = {
    "player": {
        "id": 1,
        "hand": ["Qs", "3d"],
        "bankroll": 3,
        "betamt": 0,
        "ingame": 1,
    },
    "players": [],
    "call_value": 2,
    "players_playing": 5,
    "community_cards": [],
    "pot": 0,
    "round": 0,
    "max_bet": 3,
}

test_state_4 = {
    "player": {
        "id": 1,
        "hand": ["Qs", "3d"],
        "bankroll": 1,
        "betamt": 0,
        "ingame": 1,
    },
    "players": [],
    "call_value": 2,
    "players_playing": 5,
    "community_cards": [],
    "pot": 0,
    "round": 1,
    "max_bet": 1,
}


class TestUtilities(unittest.TestCase):
    def testDefectiveSystemResponse(self):
        test_state = {
            "player": {
                "id": 1,
                "hand": ["Ac", "9s"],
                "bankroll": 100,
                "betamt": 0,
                "ingame": 1,
            },
            "players": [],
            "call_value": 9,
            "players_playing": 2,
            "community_cards": [],
            "pot": 24,
            "round": 0,
            "max_bet": 100,
        }

        self.assertEqual(systemResponse(test_state), 1)

    def testCooperativeSystemResponse(self):
        test_state = {
            "player": {
                "id": 1,
                "hand": ["Ac", "9s"],
                "bankroll": 100,
                "betamt": 0,
                "ingame": 1,
            },
            "players": [],
            "call_value": 0,
            "players_playing": 2,
            "community_cards": [],
            "pot": 3,
            "round": 0,
            "max_bet": 100,
        }

        self.assertEqual(systemResponse(test_state), 0)

    def testDefectiveMoves(self):

        self.assertEqual(prodigalMove(test_state_0), ("r", 10))
        self.assertEqual(prodigalMove(test_state_1), ("b", 10))
        self.assertEqual(prodigalMove(test_state_2), ("r", 50))
        self.assertEqual(prodigalMove(test_state_3), ("a", -1))
        self.assertEqual(frugalMove(test_state_4), ("a", -1))

    def testCooperativeMoves(self):

        self.assertEqual(frugalMove(test_state_0), ("ch", -1))
        self.assertEqual(frugalMove(test_state_1), ("ch", -1))
        self.assertEqual(frugalMove(test_state_2), ("c", -1))
        self.assertEqual(frugalMove(test_state_3), ("c", -1))
        self.assertEqual(frugalMove(test_state_4), ("a", -1))

    def testAvailableMoves(self):
        result_0 = set(availableMoves(test_state_0))
        expected_0 = set([("r", 10), ("ch", -1), ("f", -1)])
        try:
            self.assertTrue(all(elem in result_0 for elem in expected_0))
        except AssertionError:
            print(
                f"Error in test_state_0: Result={result_0}, Expected={expected_0}")

        result_1 = set(availableMoves(test_state_1))
        expected_1 = set([("b", 10), ("ch", -1), ("f", -1)])
        try:
            self.assertTrue(all(elem in result_1 for elem in expected_1))
        except AssertionError:
            print(
                f"Error in test_state_1: Result={result_1}, Expected={expected_1}")

        result_2 = set(availableMoves(test_state_2))
        expected_2 = set([("r", 50), ("c", -1), ("f", -1)])
        try:
            self.assertTrue(all(elem in result_2 for elem in expected_2))
        except AssertionError:
            print(
                f"Error in test_state_2: Result={result_2}, Expected={expected_2}")

        result_3 = set(availableMoves(test_state_3))
        expected_3 = set([("a", -1), ("c", -1), ("f", -1)])
        try:
            self.assertTrue(all(elem in result_3 for elem in expected_3))
        except AssertionError:
            print(
                f"Error in test_state_3: Result={result_3}, Expected={expected_3}")

        result_4 = set(availableMoves(test_state_4))
        expected_4 = set([("a", -1), ("f", -1)])
        try:
            self.assertTrue(all(elem in result_4 for elem in expected_4))
        except AssertionError:
            print(
                f"Error in test_state_4: Result={result_4}, Expected={expected_4}")


if __name__ == "__main__":
    unittest.main()
