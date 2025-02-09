from poker_metrics import frugalMove, privateValue, prodigalMove, odds
from poker_metrics.potential.potential import potential

import random

class Strategy:
    def __init__(self):
        """
            Initializes all the required variables for easy access by children classes.
            
            This constructor initializes various attributes of the `Strategy` class, including:
            
            - `eval`: A boolean flag indicating whether the strategy is being used for automated data generation.
            - `iniLimitMultiplier`: A variable used for setting the initial limit.
            - `seed`: The seed value for the strategy.
            - `information`: A dictionary containing game information.
            - `holeCards`: The player's hole cards.
            - `communityCards`: The community cards.
            - `round`: The current round of the game.
            - `prevActionRound`: The previous action round.
            - `callValue`: The current call value.
            - `playerBetAmt`: The total amount the player has bet in the current hand.
            - `pot`: The current pot size.
            - `initialPot`: The initial pot size, used for limiting the pot.
            - `betAmt`: The additional amount the player will bet or raise.
            - `bigBlind`: The big blind value.
            - `hs`, `sp`, `po`, `effectivePotential`: Metrics used for decision making and placing bets.
            - `shift`, `risk`: Numbers defining the "prodigalness", "frugalness", and risk capacity of the strategy.
            - `bluff`: A flag indicating whether the player should bluff.
            - `move`: The move the player will make.
            - `defaultLimit`: The default limit for the strategy.
        """
        
        # If eval True then strategy is being used for automated data generation
        self.eval = False
        self.inspector = None

        # Variables for initial limit
        self.iniLimitMultiplier = -1

        self.seed = None

        self.information = {}

        self.holeCards = []
        self.communityCards = []

        # Initialised to -1 for distinction
        self.round = -1
        self.prevActionRound = -1
        self.callValue = -1

        # This is the total amount that the player has bet in a give hand (pre-flop to present round)
        self.playerBetAmt = -1

        self.pot = 0
        self.initialPot = 0     # Required for limiting pot

        # This is the additional amount that the player will bet/raise
        self.betAmt = 0
        self.bigBlind = 0

        # Metrics for decision making and placing bets
        self.hs = -1
        self.sp = -1
        self.ps = 0
        self.ll = 0
        self.ul = 0
        self.ul_ = 0
        self.mu = 0
        self.r = None

        # A number defining the "prodigalness/frugalness" of a strategy
        self.shift = 0

        # A number defining the risk capacity of a strategy
        self.risk = 0

        self.bluff = 0                    # If true then bluff

        self.move = ()

        self.defaultLimit = 100000

    def initialise(self, information):
        """
            Initializes the strategy with the provided game information.
    
            This method is responsible for setting up the initial state of the strategy based on the information provided in the `information` dictionary. It extracts and sets various attributes of the strategy, such as the player's hole cards, the community cards, the current round, the big blind, the call value, the player's bet amount, the pot size, and the initial pot size.
    
            If this is the pre-flop round and the `iniLimitMultiplier` is greater than 0, the method sets the `limit` attribute based on the initial pot size. Otherwise, it sets the `limit` to the `defaultLimit`.
    
            After setting the initial state, the method calls several other methods (`reason()`, `setBet()`, `limiter()`, `toBlinds()`, `setMove()`) to further process the game information and determine the strategy's move.
    
            Finally, the method checks if the calculated bet amount (`self.betAmt`) is greater than the `limit`, and raises an exception if it is.
        """

        self.information = information
        if information["seed"]:
            self.seed = round(information["seed"])

        self.holeCards = information["player"]["hand"]
        self.communityCards = information["community_cards"]

        self.round = information["round"]
        self.bigBlind = information["blinds"]["bb"]["amt"]

        self.callValue = information["call_value"]

        # It is the amount player has bet till now
        self.playerBetAmt = information["player"]["betamt"]

        self.pot = information["pot"]

        self.setInitialPot()

        # If this is the pre-flop then set initial limit
        if (self.round == 0) and (self.iniLimitMultiplier > 0):
            self.limit = self.iniLimitMultiplier*self.initialPot
        else:
            # Else set default limit as limit
            self.limit = self.defaultLimit

        # Check the README for insight into the following methods
        self.reason()
        self.setBet()
        self.toBlinds()
        self.limiter()
        self.setMove()

        # This statement checks for error
        # NOTE: In some rare cases the betAmt may be greater by 1BB or a very small size
        if (self.betAmt > self.limit):
            raise Exception(f"{self.betAmt} {self.limit}")

        self.prevActionRound = self.round

    def decide(self, information):
        """
            Decides the action to take based on the current game state.
            
            This function is responsible for initializing the game state and returning the appropriate move to make. If the `eval` attribute is set to `True`, the function will initialize the game state using the provided `information` dictionary and return the calculated move. If `eval` is `False`, a `NotImplementedError` is raised indicating that the `decide` function has not been implemented for the current strategy.
        """

        # This function should be `initialised` so that it can use class variables
        if self.eval:
            # self.eval is True when the strategies are created by engine
            # Simply, it is when the strategy does not have a python file associated with it
            if information == {}:
                # Pass if there is no information
                pass
            else:
                self.initialise(information)
                if self.inspector:
                    self.inspector.trackHistory(f"{self.information['player']['id']}", f"{self.information['hand_number']}.{self.information['round']}", {
                        "hs": self.hs,
                        "sp": self.sp,
                        "mu": self.mu,
                        "ps": self.ps,
                        "ul": self.ul,
                        "betAmt": self.betAmt,
                        "callValue": self.callValue,
                        "bigBlind": self.bigBlind,
                        "ul-mu": round(self.ul - self.mu, 10), 
                        "ul-r": round(self.ul - self.r, 10)
                    })
                    # self.inspector.log()
                return self.move
        else:
            raise NotImplementedError(
                f"The decide function is not implemented by {self.strategy}")

    def reason(self):
        """
            Calculates the necessary values for determining the betting strategy.
            
            This method calculates various values that are used to determine the betting strategy, including:
            - The hand strength (`self.hs`) using the `privateValue` function.
            - Whether a bluff should be attempted (`self.bluffer`) if `self.bluff` is greater than 0.
            - The pot odds (`self.po`) based on the call value and the pot size.
            - The lower limit (`self.ll`) and upper limit (`self.ul`) of the betting range, which are derived from the pot odds and the potential (`self.sp`).
        """
                
        self.hs = round(privateValue(self.holeCards, self.communityCards), 6)

        # Bluff if true
        if self.bluff > 0:
            self.bluffer()

        self.sp = round(potential(self.holeCards, self.communityCards) if self.round in [1, 2] else 0, 6)

        self.ps = round(self.callValue/self.pot, 6)

        self.ul_ = round((self.sp + self.risk) if self.round in [1, 2] else (self.hs + self.risk), 6)
        self.mu = round((self.hs + self.shift), 6)

        # self.ul = max(self.ul_, self.mu)
        self.ul = round(max(self.ul_, self.mu), 6)
        
        # if self.ul == 0.0 and self.mu > 0.0:
        #     raise Exception()

        # self.ul = 0

        self.max_bet = round(self.ul * self.pot)

    def setBet(self):
        """
            Sets the bet amount.
        """

        if (self.ul != self.ll):
            # Get odds from the odds function and then derive the bet amount
            # The odd is decided randomly from player's playing range
            self.r = round(odds(self.ll, self.ul, self.mu), 6)

            if (self.r < self.ps):
                # Strategy is in out of money
                self.betAmt = -1
                self.r = 0
            else:
                self.monValue = round(self.pot*self.r)
                self.betAmt = min(self.monValue, self.max_bet)   
        
        else:
            # Explicitly check/fold (return -1 as bet amount)
            # Strategy is in out of money
            self.betAmt = -1
            self.r = 0

    def toBlinds(self):
        """
            Converts the monetary value to the nearest big blind multiple.
            
            - If the bet amount is explicitly a check/fold or call scenario, this method does nothing.
            - Otherwise, it calculates the bet amount relative to the call value, rounds it to the nearest big blind multiple, and updates the bet amount.
        """
        
        if self.betAmt in [-1, 0]:
            # Explicitly check/fold or call scenario
            pass
        else:
            bet = self.betAmt - self.callValue
            bet = round(bet/self.bigBlind) * self.bigBlind
        
            initBetAmt = bet + self.callValue

            while (initBetAmt > self.betAmt):
                initBetAmt -= self.bigBlind
            self.betAmt = initBetAmt

    def limiter(self):
        """
            Limits the bet amount based on the player's total bet amount and the specified limit.

            If the total bet amount (including the player's bet) exceeds the limit, the bet amount is adjusted to the maximum allowed within the limit. If the call value plus the player's bet amount exceeds the limit, the bet amount is set to 0 to force a call.
        """

        if self.betAmt in [-1, 0]:
            # Ignore limit when explicitly check or fold
            pass
        else:
            tcb = self.betAmt + self.playerBetAmt

            if tcb > self.limit:
                # req = self.callValue + self.playerBetAmt

                # if req > self.limit:
                #     # Limit passed
                #     # Forcefully call
                #     self.betAmt = 0

                # else:
                self.betAmt = self.limit - self.playerBetAmt

    def setMove(self):
        """
            Determines the move to make based on the calculated bet amount.

            - If the bet amount is -1, it means a check/fold is explicitly requested, so the move is set accordingly.
            - If the bet amount is 0 or equal to the call value, a frugal move is made.
            - If the bet amount is greater than the call value, a prodigal move is made.
            - If the bet amount is less than the call value, an exception is raised as this scenario should not occur.
            - If the bet amount is invalid, an exception is raised.
        """

        if self.betAmt == -1:
            # Check/Fold when explicitly -1
            if self.callValue == 0:
                self.move = ("ch", -1)
            else:
                self.move = ("f", -1)

        elif self.betAmt == 0 or self.betAmt == self.callValue:
            # Frugal move when bet amount is explicitly 0 or call value
            self.move = frugalMove(self.information)

        elif self.betAmt > self.callValue:
            # Prodigal move when bet amount is more than call value
            self.move = prodigalMove(
                self.information, betAmt=(self.betAmt - self.callValue))

        elif self.betAmt < self.callValue:
            # This scenario should not happen so raise an exception
            # Fold in this scenario
            self.move = ("f", -1)
            # raise Exception(
            #     f"Bet amount can't be less: {self.betAmt} >! {self.callValue}")

        else:
            raise Exception(f"Invalid bet amount: {self.betAmt}")

    def setInitialPot(self):
        """
            Sets the initial pot value for the current game round.

            This method is only applicable for heads-up games. If the current round is 0 and the previous action round is not 0, the initial pot is set to 2 times the big blind. Otherwise, the initial pot is set to -1.

            The commented-out code shows a generalised way to calculate the initial pot.
        """

        # Only applicable for heads-up
        if (self.round == 0):
            self.initialPot = 2 * self.bigBlind

            # Ideally

            # initialPot = self.bigBlind + (self.bigBlind/2)
            # self.initialPot = round(initialPot/self.bigBlind) * self.bigBlind

        else:
            self.initialPot = -1

        # Ideally

        # elif self.prevActionRound < self.round:
        #     initialPot = (self.pot - self.callValue)

        #     # Converting to blinds
        #     self.initialPot = round(initialPot/self.bigBlind) * self.bigBlind

    def bluffer(self):
        """
            Inverses a strategy's hand strength to turn weak hand to strong. 
            If the hand strength is less than 0.5, there is a 1 in `self.bluff` chance that the hand strength will be set to 1 minus the original hand strength.
        """

        # Only applicable if hand strength is less than 0.5
        if self.hs < 0.5:
            # 1 in `self.bluff` chance to inverse hand strength
            if 1 == random.randint(1, int(self.bluff)):
                self.hs = 1 - self.hs

    def __str__(self):
        return f"{self.strategy}"
