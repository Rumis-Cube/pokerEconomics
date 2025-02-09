"""
- see if every hand is zero sum
- see if every round is zero sum (total money in play - bankrolls - pot = 0)
- make a list of all possible legal transitions, and see if they are maintained
"""

import json as js


def chainValidate(debugData, handNumber):
    rawActionChain = debugData["rawActionChain"]
    config = debugData["config"]
    handChain = extractChain(rawActionChain, handNumber)
    actionsValidator(handChain)
    validator(handChain)
    roundZeroSumValidator(rawActionChain, handChain, config)


def extractChain(rawActionChain, handNumber):
    roundChain = []

    for actionData in rawActionChain:
        if actionData["hand_number"] == handNumber:
            roundChain.append(actionData)

    return roundChain


def actionsValidator(roundChain):
    """
    Validates all the actions taken in a hand.
    """

    for i in range(len(roundChain)):

        # Validate the first action (Can only call, raise, all-in, or fold)
        if i == 0:
            action = roundChain[i]["action"]
            playerId = roundChain[i]["player"]["id"]
            condition = (
                (action == "c") or (action == "r") or (action == "a") or (action == "f")
            )

            assert (
                condition
            ), f"Player {playerId} made an invalid move {action} on first move."
        else:
            priorActionData = roundChain[i - 1]
            presentActionData = roundChain[i]

            presentPlayer = presentActionData["player"]

            action = presentActionData["action"]
            priorAction = priorActionData["action"]

            if priorActionData["round"] == presentActionData["round"]:

                if action == "c":
                    legalPriorActions = ["r", "b", "c", "a"]
                    actionAssert(
                        action, priorAction, legalPriorActions, presentPlayer["id"]
                    )

                elif action == "ch":
                    condition = (
                        priorAction in ["c", "ch", "a", "f"]
                        and presentActionData["call_size"] == 0
                    )
                    assert (
                        condition
                    ), "Player is not checking appropriately in {}".format(
                        presentActionData
                    )

                elif action == "r":
                    legalPriorActions = ["b", "c", "r"]
                    actionAssert(
                        action, priorAction, legalPriorActions, presentPlayer["id"]
                    )

                elif action == "b":
                    legalPriorActions = ["ch"]
                    actionAssert(
                        action, priorAction, legalPriorActions, presentPlayer["id"]
                    )
            else:
                # This is when it is the first hand of a specific round
                legalActions = ["b", "ch", "a", "f"]
                assert (
                    action in legalActions
                ), "Player {} cannot {} in first action of a round.".format(
                    presentPlayer["id"], action
                )


def roundZeroSumValidator(rawActionChain, roundChain, config):
    bankrollSum = config["player1"]["bankroll"] + config["player2"]["bankroll"]

    if rawActionChain:
        p2bankroll = 0

        # If someone folds in the first action
        plist = roundChain[-1]["players"]

        for player in plist:
            if roundChain[-1]["player"]["id"] != player["id"]:
                p2bankroll = player["bankroll"]

        condition = (
            bankrollSum
            - roundChain[-1]["pot_after"]
            - roundChain[-1]["player"]["bankroll"]
            - p2bankroll
        )

        assert condition == 0, "Round zero sum validator (return {}) failed.".format(
            condition
        )


def validator(handChain):
    """
    Validates each specific metrics of each hands.
    """

    for i in range(len(handChain)):
        # Pass if it is the first action of a game or the last winning action

        actionData = handChain[i]

        # Pot validation
        pot0SumCondition = actionData["pot_after"] - (
            actionData["pot_before"]
            + (actionData["bet"] if (actionData["bet"] != -1) else 0)
            + (actionData["call_size"] if (actionData["action"] in ["c", "ch"]) else 0)
        )

        assert (
            pot0SumCondition == 0
        ), "Pot zero sum condition (returned {}) failed in action: \n{}".format(
            pot0SumCondition, actionData
        )

        # Bankroll Validation
        bld = actionData["blind"]

        bankroll0SumCondition = (
            actionData["player_prev_bankroll"]
            - actionData["player"]["bankroll"]
            - (
                actionData["bet"]
                if actionData["bet"] != -1
                else (
                    actionData["call_size"]
                    if (actionData["action"] in ["c", "ch"])
                    else 0
                )
            )
            - bld
        )

        assert (
            bankroll0SumCondition == 0
        ), "Bankroll zero sum condition (returned {}) failed in action: \n {}".format(
            bankroll0SumCondition, actionData
        )

        roundChain = roundChainExtractor(handChain, actionData["round"])
        callValidator(roundChain)


def callValidator(roundChain):
    """

    ### Call size validator

    Based on the idea a player need to match the bet of previous player at any point of the game.\n
    `Formula:` (CallSize + TotalBetAmountOfPlayer) - (OpponentTotalBetAmount) = (CallSize + (Pot/0{conditionally} - OpponentTotalBet)) - OpponentTotalBet\n
    `Simplified Formula:` CallSize + Pot/0{conditionally} - 2*OpponentTotalBetAmount\n

    """
    potEqualiser = 0

    if roundChain:
        if roundChain[0]["round"] != 0:
            potEqualiser = roundChain[0]["pot_before"]

    for i in range(len(roundChain)):
        if i >= 1:
            actionData = roundChain[i]
            priorActionData = roundChain[i - 1]

            callSize = actionData["call_size"]
            pot = actionData["pot_before"] - potEqualiser
            oppTotalBetAmt = priorActionData["player"]["betamt"]

            if callSize == oppTotalBetAmt == 0:
                pot = 0

            call0SumCondition = callSize + pot - 2 * oppTotalBetAmt

            assert (
                call0SumCondition == 0
            ), "Call zero sum condition (returned {}) failed in action: \n{}".format(
                call0SumCondition, actionData
            )


def roundChainExtractor(handChain, round_num):
    roundChain = []

    for action in handChain:
        if action["round"] == round_num:
            roundChain.append(action)

    return roundChain


def actionAssert(presentAction, priorAction, legalPriorActions, playerId):

    condition = priorAction in legalPriorActions

    assert condition, "Player {} cannot {} when prior action is {}.".format(
        playerId, presentAction, priorAction
    )


def extractRoundChain(roundChain):
    rounds = []
    currentRound = -1
    for action in roundChain:
        roundNumber = action["round"]
        if roundNumber != currentRound:
            rounds.append([])
            currentRound = roundNumber
        rounds[-1].append(action)
    return rounds
