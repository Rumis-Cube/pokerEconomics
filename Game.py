import os
import json
import sys
import traceback
from tqdm import tqdm

from tests.system_checks import chainValidate, extractChain
from components.Deck import Deck
from components.Showdown import Showdown

# Disable print
def blockPrint():
    sys.stdout = open(os.devnull, "w")


# Restore print
def enablePrint():
    sys.stdout = sys.__stdout__


class Game:
    def __init__(
        self,
        players,
        logger,
        inspector=None,
        number_of_hands=1,
        deck=Deck,
        simul=False,
        seed=None,
        id=0,
        config={},
        test=False
        ):
        self.seed = seed
        self.id = id
        self.config = config
        self.deck = deck(seed)
        self.deck.shuffle()
        self.pot = 0
        self.players = players
        self.number_of_players = len(players)
        self.community_cards = []
        self.simul = simul
        self.round = 0
        self.logger = logger
        self.inspector = inspector
        self.hand_number = 0
        self.all_in = 0
        self.number_of_hands = number_of_hands
        self.test = test
        self.debug_data = []
        self.actionChain = list()
        self.roundFirstAction = None
        self.firstDeterminer = []
        self.stats = {}
        # rounds are 0-indexed starting with pre-flop
        # counts the number of players currently in a game [later gets flushed]
        self.playing = len(players)
        self.blind = {}
        logger.log_config(players, number_of_hands, self.deck.seed)

    def get_max_bet(self, player_index):
        """
        Finds the maximum amount a player can bet.
        """
        current_player = self.players[player_index]

        # Initialising to 0 and then finding the max bankroll of all players
        max_bet = 0
        for i in range(len(self.players)):
            player = self.players[i]
            if player.ingame and i != player_index:
                max_bet = max(max_bet, player.bankroll)

        # Maximum amount that can be bet is the minimum of player's bankroll and the max_bet obtained
        max_bet = min(max_bet, current_player.bankroll)

        return max_bet

    def package_state(
        self, player_index, call_value=0
    ):  # 0 call values indicate no bets being placed before this
        player = self.players[player_index]

        if not self.firstDeterminer:
            # Pre-flop
            # Player starting in the pre-flop in heads-up is the one to always start each betting round
            self.roundFirstAction = True
            self.firstDeterminer = [self.round, player_index]
        else:
            # When round greater than determiner then betting stage changed
            if self.round > self.firstDeterminer[0]:
                # Only the opening player can take the first action
                if self.firstDeterminer[1] == player_index:
                    self.roundFirstAction = True
                    self.firstDeterminer = [self.round, player_index]

                self.roundFirstAction = False
            else:
                self.roundFirstAction = False

        return {
            "player": player.package_state(),
            "call_value": call_value,
            "players_playing": len(self.players),
            "players": self.players,
            "community_cards": self.community_cards,
            "pot": self.pot,
            "hand_number": self.hand_number,
            "round": self.round,
            "max_bet": self.get_max_bet(player_index),
            "blinds": self.blind,
            "roundFirstAction": self.roundFirstAction,
            "seed": self.seed
        }

    def flush(self):
        """
        Resets the game.
        """
        self.deck.flush()

        for player in self.players:
            player.flush()

        self.community_cards = []

        self.round = 0
        self.playing = len(self.players)
        self.all_in = 0

    def sub_play(self, i):
        """
        Takes hand_number as input and determines whether game ended or not.\n
        Returns 0 if game ended else returns 1.
        """
        self.hand_number = i
        self.logger.handle_hand_file(i)
        # Determining the number of players available to play
        count = len(self.players)
        for player in self.players:
            if player.bankroll == 0:
                count -= 1

        # Exit the game and return 0 if a winner emerges
        if count == 1:
            self.logger.print("Insufficient players")
            return 0

        # Keep a track of all the players' bankroll and proceed to pre-flop
        bankrolls = {player.id: player.bankroll for player in self.players}
        for id in bankrolls:
            self.logger.print(f"{id}: {bankrolls[id]}")
        self.preflop()

        # Flush and rotate dealer after pre-flop
        self.logger.log_hand()
        self.flush()
        self.players = self.players[-1:] + self.players[:-1]
        self.pot = 0
        return 1

    def play(self, benchmark=False):
        try:
            if benchmark and self.simul:
                blockPrint()
                for i in range(self.number_of_hands):
                    if not self.sub_play(i):
                        break
                enablePrint()
            elif self.simul:
                blockPrint()
                with tqdm(
                    total=self.number_of_hands,
                    desc=f"Simulation ##{self.id}: ",
                    position=self.id,
                    colour='#00ff00',
                ) as pbar:
                    for i in range(self.number_of_hands):
                        if self.test:
                            self.debug_data = {
                                "config": self.config,
                                "rawActionChain": self.actionChain,
                            }
                            chainValidate(self.debug_data, self.hand_number)

                        if not self.sub_play(i):
                            break

                        pbar.update(1)
                        
                enablePrint()
            else:
                for i in range(self.number_of_hands):
                    if not self.sub_play(i):
                        break
            self.logger.close_files()
        except Exception as e:
            trc = traceback.format_exc()
            self.logger.log_error(trc)

    def player_bet(self, player, amt):
        """
        Increments the pot by the bet amount whenever a player bets.\n
        Takes the player object and bet amount as input.
        """

        if player in self.players:
            returnValue = player.bet(amt)

            # Error checks with the player's bet method
            if returnValue == False:
                return False

            self.pot += returnValue

    def check_stack(self, betsize):
        """
        Checks whether player's stack is more/less than bankroll.\n
        Return 0 if exceeded, else 1.
        """

        for j in range(len(self.players)):
            if self.players[j].ingame == 1:
                if betsize > self.players[j].bankroll:
                    self.logger.print("Effective Stack size exceeded")
                    # Return 0 if exceeded
                    return 0

        # Return 1 if not
        return 1

    def check_betsize(self, betsize, callsize):
        """
        Confirms that bet size is greater than call value.
        """

        while 1:
            if betsize <= callsize:
                betsize = int(
                    input(
                        "Bet-size cannot be less than or equal to call-size try again:"
                    )
                )
            else:
                return betsize

    def actionStash(
        self,
        pot_before,
        player_prev_bankroll,
        action,
        call_value,
        player,
        betAmt=-1,
        blind=0,
    ):
        """
        To be called after an action takes place.
        """
        if self.test:
            actionData = {
                "hand_number": self.hand_number,
                "round": self.round,
                "pot_before": pot_before,
                "player_prev_bankroll": player_prev_bankroll,
                "action": action,
                "call_size": call_value,
                "bet": betAmt,
                "pot_after": self.pot,
                "blind": blind,
                "player": player.to_dict(),
                "players": [player.to_dict() for player in self.players],
            }

            self.actionChain.append(actionData)

    def HUDdetails(self, bettingData):
        pot = bettingData["pot"]
        bet = bettingData["bet"]
        player = [_player for _player in self.players if _player.id ==
                  bettingData["player"]][0]
        # player = player[0]
        action = bettingData["action"]
        frugality = 0
        # opp = [_player for _player in self.players if _player != player]
        # opp = opp[0]
        if (action == "b"):
            frugality = bet/pot + bet/player.bankroll
        if (action == "r"):
            frugality = (bet/pot + bet/player.bankroll)/2
        player.frugal += frugality
        player.meanFrugal = player.frugal / self.number_of_hands

    def betting(self, players, betsize=0):
        """
        Handles the betting round.\n
        Returns 0 if betting round completed.
        """

        # The last player where the action finishes
        end = self.playing - 1
        i = 0
        betting_data = []
        while 1:
            # Printing information before a bet/call
            self.logger.print(f"\nPot: {self.pot}")
            self.logger.print(
                f"Number of Players Playing: {self.playing}",
            )
            self.logger.print(
                f"Number of Players All-In: {self.all_in}",
            )

            # Finding out the current player
            player_index = i % len(players)
            player = players[player_index]

            # Printing out the bankroll of the current player
            self.logger.print(
                f"{player.id}'s Bankroll: {player.bankroll}",
            )

            # Figuring out the call size and printing more information
            callsize = betsize - player.betamt
            self.logger.print(
                f"Player's present total bet amount: {player.betamt}",
            )
            self.logger.print(f"Call size: {callsize}")

            current_betting_option_data = {
                "pot": self.pot,
                "num_players": self.playing,
                "num_players_allin": self.all_in,
                "player": player.id,
                "callsize": callsize,
                "present_total_bet": player.betamt,
                "action": "",
                "bet": -1,
                "bankroll": player.bankroll,
            }

            # Check if the player is still in the current game
            if player.ingame == 0:
                # If not then move to next player
                i = (i + 1) % len(players)
                betting_data.append(current_betting_option_data)
                continue

            # If not then move to the next player
            if player.bankroll == 0:
                # If all players have gone all in then break
                if self.all_in >= self.playing - 1:
                    betting_data.append(current_betting_option_data)
                    break

                # Else move to next player
                i = (i + 1) % len(players)
                betting_data.append(current_betting_option_data)
                continue

            # Print out the options
            self.logger.print(
                f"{player.id}'s action -> call(c) / check(ch) / bet(b) / raise(r) / fold(f) / all in(a): ",
            )

            # If simulation then get the action from the decide function (strategy)
            if self.simul:
                # Ensure player stats are initialized
                if f"{player.id}" not in self.stats:
                    self.stats = {players[0].id: {"b": 0, "r": 0, "c": 0, "ch": 0, "f": 0}, players[1].id: {"b": 0, "r": 0, "c": 0, "ch": 0, "f": 0}}
    
                action, bet = player.decide(
                    self.package_state(player_index, call_value=callsize)
                )
                
                if action in self.stats[f"{player.id}"]:
                    self.stats[f"{player.id}"][action] += 1
                else:
                    self.stats[f"{player.id}"][action] = 1

                self.logger.print(action)
            else:
                action = input()  # Else take input from cli
            # self.updateHud(self.round, action,player,self.players)
            current_betting_option_data["action"] = action
            # If action is call
            if action == "c":
                if self.test:
                    player_prev_bankroll = player.bankroll

                    blind = 0

                    handChain = extractChain(
                        self.actionChain, handNumber=self.hand_number
                    )

                    if len(handChain) == 0 or len(handChain) == 1:
                        if (
                            player.id == self.blind["bb"]["player"]
                            or player.id == self.blind["sb"]["player"]
                        ):
                            if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                blind = self.blind["bb"]["amt"]
                                player_prev_bankroll += blind
                            elif callsize == (
                                self.blind["bb"]["amt"] -
                                    self.blind["sb"]["amt"]
                            ):
                                blind = self.blind["sb"]["amt"]
                                player_prev_bankroll += blind

                    pot_before = self.pot

                # Action only valid if call size is not 0 (check is then appropriate)
                if callsize != 0:
                    # If bankroll less than call size then player goes all in
                    if player.bankroll <= callsize:
                        self.player_bet(player, player.bankroll)
                        self.all_in += 1
                    else:
                        self.player_bet(
                            player, callsize
                        )  # Else allow to "bet" (call the full amount)

                    if self.test:
                        self.actionStash(
                            pot_before,
                            player_prev_bankroll,
                            action,
                            callsize,
                            player,
                            bet,
                            blind=blind,
                        )
                else:
                    self.logger.print("Illegal move")
                    i = (i + len(players)) % len(players)
                    current_betting_option_data["err"] = "Illegal move"
                    betting_data.append(current_betting_option_data)
                    continue

            # If action is check
            elif action == "ch":
                if callsize == 0:
                    if self.test:
                        player_prev_bankroll = player.bankroll

                        blind = 0

                        handChain = extractChain(
                            self.actionChain, handNumber=self.hand_number
                        )

                        if len(handChain) == 0 or len(handChain) == 1:
                            if (
                                player.id == self.blind["bb"]["player"]
                                or player.id == self.blind["sb"]["player"]
                            ):
                                if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                    blind = self.blind["bb"]["amt"]
                                    player_prev_bankroll += blind
                                elif callsize == (
                                    self.blind["bb"]["amt"] -
                                        self.blind["sb"]["amt"]
                                ):
                                    blind = self.blind["sb"]["amt"]
                                    player_prev_bankroll += blind

                        pot_before = self.pot

                        self.actionStash(
                            pot_before,
                            player_prev_bankroll,
                            action,
                            callsize,
                            player,
                            bet,
                            blind=blind,
                        )
                else:
                    self.logger.print("Illegal move")
                    i = (i + len(players)) % len(players)
                    current_betting_option_data["err"] = "Illegal move"
                    betting_data.append(current_betting_option_data)
                    continue

            # If action is bet
            elif action == "b":
                if self.test:
                    player_prev_bankroll = player.bankroll

                    blind = 0

                    handChain = extractChain(
                        self.actionChain, handNumber=self.hand_number
                    )

                    if len(handChain) == 0 or len(handChain) == 1:
                        if (
                            player.id == self.blind["bb"]["player"]
                            or player.id == self.blind["sb"]["player"]
                        ):
                            if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                blind = self.blind["bb"]["amt"]
                                player_prev_bankroll += blind
                            elif callsize == (
                                self.blind["bb"]["amt"] -
                                    self.blind["sb"]["amt"]
                            ):
                                blind = self.blind["sb"]["amt"]
                                player_prev_bankroll += blind

                    pot_before = self.pot

                # Confirms if player's total bet amount is 0
                if player.betamt == 0:
                    # Takes the bet amount
                    self.logger.print(f"Enter the bet: ")

                    # Take input from cli if not simulation
                    if not self.simul:
                        bet = int(input())

                    # Bet cannot be negative
                    if bet <= 0:
                        self.logger.print("Bet size cannot be less than or equal to zero")
                        i = (i + len(players)) % len(players)
                        current_betting_option_data["err"] = "Bet size cannot be less than or equal to zero"
                        betting_data.append(current_betting_option_data)
                        continue

                    # Prints the bet amount
                    self.logger.print(bet)
                    current_betting_option_data["bet"] = bet
                    # If bankroll less than bet amount then player goes all in
                    if player.bankroll <= bet:
                        bet = player.bankroll
                        self.all_in += 1

                    # Checks if stack exceeded or not
                    if self.check_stack(bet - callsize) == 0:
                        i = (i + len(players)) % len(players)
                        betting_data.append(current_betting_option_data)
                        continue

                    # Bet's the total bet amount
                    betsize = bet + player.betamt
                    self.player_bet(player, bet)

                    # Prints the total bet size and sets the loop to end on player before this
                    self.logger.print(
                        f"Player's current total bet size: {betsize}",
                    )
                    end = (i - 1) % len(players)
                    self.HUDdetails(current_betting_option_data)
                    if self.test:
                        self.actionStash(
                            pot_before,
                            player_prev_bankroll,
                            action,
                            callsize,
                            player,
                            bet,
                            blind=blind,
                        )
                else:
                    self.logger.print("Illegal move")
                    i = (i + len(players)) % len(players)
                    current_betting_option_data["err"] = "Illegal move"
                    betting_data.append(current_betting_option_data)
                    continue

            # If action is raise
            elif action == "r":
                if self.test:
                    player_prev_bankroll = player.bankroll

                    blind = 0

                    handChain = extractChain(
                        self.actionChain, handNumber=self.hand_number
                    )

                    if len(handChain) == 0 or len(handChain) == 1:
                        if (
                            player.id == self.blind["bb"]["player"]
                            or player.id == self.blind["sb"]["player"]
                        ):
                            if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                blind = self.blind["bb"]["amt"]
                                player_prev_bankroll += blind
                            elif callsize == (
                                self.blind["bb"]["amt"] -
                                    self.blind["sb"]["amt"]
                            ):
                                blind = self.blind["sb"]["amt"]
                                player_prev_bankroll += blind

                    pot_before = self.pot

                # If betsize greater than 0 only then raise is allowed (else bet is appropriate)
                if betsize > 0:
                    # Inputs the raise
                    self.logger.print(f"Enter the raise: ")

                    if not self.simul:
                        bet = int(input())

                    # Bet size cannot be negative
                    if bet <= 0:
                        self.logger.print("Raise size cannot be less than or equal to zero")
                        i = (i + len(players)) % len(players)
                        current_betting_option_data["err"] = "Raise cannot be less than or equal to zero"
                        betting_data.append(current_betting_option_data)
                        continue

                    # Print bet amount
                    self.logger.print(bet)
                    current_betting_option_data["bet"] = bet
                    # If bankroll is less than bet then player goes all in
                    if player.bankroll <= bet:
                        bet = player.bankroll
                        self.all_in += 1

                    # Checks stack exceeded or not
                    if self.check_stack(bet - callsize) == 0:
                        i = (i + len(players)) % len(players)
                        betting_data.append(current_betting_option_data)
                        continue

                    # Bets the effective bet amount
                    betsize = bet + player.betamt
                    self.player_bet(player, bet)

                    # Prints the total bet size and sets the loop to end on player before this
                    self.logger.print(
                        f"Player's current total bet size: {betsize}",
                    )
                    end = (i - 1) % len(players)
                    self.HUDdetails(current_betting_option_data)
                    if self.test:
                        self.actionStash(
                            pot_before,
                            player_prev_bankroll,
                            action,
                            callsize,
                            player,
                            bet,
                            blind=blind,
                        )

                else:
                    self.logger.print("Illegal move")
                    i = (i + len(players)) % len(players)
                    current_betting_option_data["err"] = "Illegal move"
                    betting_data.append(current_betting_option_data)
                    continue

            # If action is fold
            elif action == "f":
                if self.test:
                    player_prev_bankroll = player.bankroll

                    blind = 0

                    handChain = extractChain(
                        self.actionChain, handNumber=self.hand_number
                    )

                    if len(handChain) == 0 or len(handChain) == 1:
                        if (
                            player.id == self.blind["bb"]["player"]
                            or player.id == self.blind["sb"]["player"]
                        ):
                            if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                blind = self.blind["bb"]["amt"]
                                player_prev_bankroll += blind
                            elif callsize == (
                                self.blind["bb"]["amt"] -
                                    self.blind["sb"]["amt"]
                            ):
                                blind = self.blind["sb"]["amt"]
                                player_prev_bankroll += blind

                    pot_before = self.pot

                # Resets player's position in the game
                player.ingame = 0
                self.playing -= 1

                if self.test:
                    self.actionStash(
                        pot_before,
                        player_prev_bankroll,
                        action,
                        callsize,
                        player,
                        bet,
                        blind=blind,
                    )

                # If only one person is playing then determines the winner (the sole person)
                if self.playing == 1:
                    winner = ""

                    for player in players:
                        if player.ingame == 1:
                            winner = player.id

                            # Add the pot to player's bankroll
                            player.bankroll += self.pot

                    # Initiate gameover method
                    self.gameover(winner)

                    betting_data.append(current_betting_option_data)
                    # Returns 0 to confirm game ended
                    return 0, betting_data

                # If there is only one person playing then game over (will be handled by betting function)
                if i == end:
                    end = (i - 1) % len(players)
                    self.logger.print(f"end is -> {end}")
                    betting_data.append(current_betting_option_data)
                    break

            # If action is all-in
            elif action == "a":
                if self.test:
                    player_prev_bankroll = player.bankroll

                    blind = 0

                    handChain = extractChain(
                        self.actionChain, handNumber=self.hand_number
                    )

                    if len(handChain) == 0 or len(handChain) == 1:
                        if (
                            player.id == self.blind["bb"]["player"]
                            or player.id == self.blind["sb"]["player"]
                        ):
                            if callsize == 0 or callsize > self.blind["sb"]["amt"]:
                                blind = self.blind["bb"]["amt"]
                                player_prev_bankroll += blind
                            elif callsize == (
                                self.blind["bb"]["amt"] -
                                    self.blind["sb"]["amt"]
                            ):
                                blind = self.blind["sb"]["amt"]
                                player_prev_bankroll += blind

                    pot_before = self.pot

                # Player bets their bankroll
                bet = player.bankroll
                betsize = bet + player.betamt

                self.logger.print(f"Player's current total bet size: {bet}")

                # Bets the player's bankroll
                self.all_in += 1
                self.player_bet(player, bet)

                end = (i - 1) % len(players)

                if self.test:
                    self.actionStash(
                        pot_before,
                        player_prev_bankroll,
                        action,
                        callsize,
                        player,
                        bet,
                        blind=blind,
                    )

            else:
                self.logger.print("invalid Input")
                i = (i + len(players)) % len(players)
                current_betting_option_data["err"] = "Illegal move"
                betting_data.append(current_betting_option_data)
                continue

            # If only one person is playing then determines the winner (the sole person)
            if self.playing == 1:
                winner = ""

                for player in players:
                    if player.ingame == 1:
                        winner = player.id

                        # Add the pot to player's bankroll
                        player.bankroll += self.pot

                # Initiate gameover method
                self.gameover(winner)

                # Returns 0 to confirm game ended
                betting_data.append(current_betting_option_data)
                return 0, betting_data

            betting_data.append(current_betting_option_data)
            # Exit condition for the loop when all the players have called
            if i == end:
                break

            # Change player index to next player and loop over
            i = (i + 1) % len(players)
        return 1, betting_data

    def preflop(self):
        """
        Handles the pre-flop action.\n
        Automatically proceeds to flop if betting round does not give 0.
        """

        # Determines the active players
        for player in self.players:
            if player.bankroll == 0:
                player.ingame = 0

        bet_size = 2

        # Determines the blinds
        bb_player = self.players[1]
        sb_player = self.players[0]
        sb_amt = min(1, sb_player.bankroll)
        bb_amt = min(2 * sb_amt, bb_player.bankroll)

        # Determines if players went all-in
        if sb_player.bankroll == sb_amt:
            self.all_in += 1
        if bb_player.bankroll == bb_amt:
            self.all_in += 1

        # Bets the blind amount from player
        self.player_bet(bb_player, bb_amt)
        self.player_bet(sb_player, sb_amt)

        self.blind = {
            "bb": {"player": bb_player.id, "amt": bb_amt},
            "sb": {"player": sb_player.id, "amt": sb_amt},
        }

        self.logger.print("\n----BLINDS-----\n")

        for player in self.players:
            self.logger.print(f"{player.id}'s blind -> {player.betamt}")

        self.logger.current_hand_data.update(
            {
                "blinds": {
                    "bankrolls": {
                        player.id: player.bankroll for player in self.players
                    },
                    "blinds": {player.id: player.betamt for player in self.players},
                }
            }
        )

        self.logger.print("\n-------PRE-FLOP------\n")
        for i in range(self.number_of_players):
            self.players[i].receive_card(self.deck.deal_card())
            self.players[i].receive_card(self.deck.deal_card())

        # Print the cards of players
        for i in range(self.number_of_players):
            self.logger.print(f"{self.players[i].id}'s cards")

            for card in self.players[i].hand:
                self.logger.print(card, end=" ")

            self.logger.print("")
        # Proceed to flop conditionally after betting
        ret = self.betting(self.players, bet_size)

        self.logger.current_hand_data.update(
            {
                "pre-flop": {
                    "bankrolls": {
                        player.id: player.bankroll for player in self.players
                    },
                    "cards": {player.id: player.hand for player in self.players},
                    "betting": ret[1],
                }
            }
        )

        if ret[0]:
            self.flop()

    def flop(self):
        """
        Handles the flop action.
        """
        self.logger.print("\n-------------FLOP-------------\n")

        # Change round and reset bet amounts
        self.round = 1
        for player in self.players:
            player.betamt = 0

        # Displaying the flop
        for _ in range(3):
            self.community_cards.append(str(self.deck.deal_card()))

        # Print the community cards
        self.logger.print(self.community_cards)

        # Proceed to turn conditionally

        self.logger.current_hand_data.update(
            {
                "flop": {
                    "bankrolls": {
                        player.id: player.bankroll for player in self.players
                    },
                    "community_cards": self.community_cards,
                    "betting": [],
                }
            }
        )

        if self.all_in >= self.playing - 1:
            self.turn()
        else:
            ret = self.betting(self.players)
            self.logger.current_hand_data["flop"]["betting"] = ret[1]
            if ret[0]:
                self.turn()

    def turn(self):
        """
        Handles the turn action.
        """
        self.logger.print("\n-------------TURN-------------\n")

        # Change round and reset bet amounts
        self.round = 2
        for player in self.players:
            player.betamt = 0

        # Add a single card
        self.community_cards.append(str(self.deck.deal_card()))

        self.logger.print(self.community_cards)

        self.logger.current_hand_data.update(
            {
                "turn": {
                    "bankrolls": {
                        player.id: player.bankroll for player in self.players
                    },
                    "community_cards": self.community_cards,
                    "betting": [],
                }
            }
        )

        # Proceed to river conditionally
        if self.all_in >= self.playing - 1:
            self.river()
        else:
            ret = self.betting(self.players)
            self.logger.current_hand_data["turn"]["betting"] = ret[1]
            if ret[0]:
                self.river()

    def river(self):
        """
        Handles the river action.
        """
        self.logger.print("\n-------------RIVER-------------\n")

        # Change round and reset bet amounts
        self.round = 3
        for player in self.players:
            player.betamt = 0

        # Add a single card
        self.community_cards.append(str(self.deck.deal_card()))
        self.logger.print(self.community_cards)

        self.logger.current_hand_data.update(
            {
                "river": {
                    "bankrolls": {
                        player.id: player.bankroll for player in self.players
                    },
                    "community_cards": self.community_cards,
                    "betting": [],
                }
            }
        )

        # Proceeds to showdown conditionally
        if self.all_in >= self.playing - 1:
            self.showdown(self.players)
        else:
            ret = self.betting(self.players)
            self.logger.current_hand_data["river"]["betting"] = ret[1]
            if ret[0]:
                self.showdown(self.players)

    def gameover(self, winner):
        """
        Displays information after the end of hand.
        """

        self.firstDeterminer = []
        self.roundFirstAction = False

        self.logger.print(f"\nWinner: {winner}")
        self.logger.print("Hand Ended")
        bankrolls = {player.id: player.bankroll for player in self.players}
        tendency = {}

        self.stats['hand_number'] = self.hand_number
        self.stats['round'] = self.round

        for player in self.players:
            pp = self.stats[player.id]["b"] + self.stats[player.id]["r"] + 0.5*self.stats[player.id]["c"]
            fp = self.stats[player.id]["ch"] + self.stats[player.id]["f"] + 0.5*self.stats[player.id]["c"]
            
            if (pp == fp == 0):
                tendency[player.id] = 0
            else:
                tendency[player.id] = (pp - fp)/(pp + fp)

        # Sorting is important since order changes after every round but logger should have consistently ordered columns in the csv
        bankrolls = dict(sorted(bankrolls.items()))
        tendency = dict(sorted(tendency.items()))

        log_data = {
            "hand_no": self.hand_number,
            "winner": winner,
            "round": self.round,
            "bankrolls": [],
            "tendency": []
        }

        self.logger.current_hand_data["gameover"] = {
            "winner": winner,
            "round": self.round,
            "bankrolls": {player.id: player.bankroll for player in self.players},
        }
        self.logger.print("")

        for id in bankrolls:
            self.logger.print(f"{id} stack: {bankrolls[id]}")
            log_data["bankrolls"].append(bankrolls[id])

        for id in tendency:
            log_data["tendency"].append(tendency[id])

        self.logger.log_result(log_data)

    def showdown(self, players):
        """
        Handles the showdown action (with the Showdown object)
        """
        s = Showdown(self.community_cards, players)
        winner = players[s.winner()]
        winner.bankroll += self.pot
        self.gameover(winner.id)
