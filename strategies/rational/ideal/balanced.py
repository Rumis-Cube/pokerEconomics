from ...Strategy import Strategy


class Ideal(Strategy):
    def __init__(self, strategyName):
        super().__init__(strategyName)

    def decide(self, information):
        self.initialise(information, tightness=0)

        r = -1

        if self.determiner >= 0:
            # In the money
            if self.privateValue >= 0.75:
                r = max(self.range)
            else:
                r = min(self.range)
        elif self.determiner < 0:
            if self.privateValue >= 0.9 and self.round in [2, 3]:
                r = 1.25
            else:
                r = min(self.range)

        move = self.strategicMove(r, information)

        # if move[0] == "r":
        #     raise Exception(f"{self.__dict__}")

        return move


strategy = Ideal("Ideal")


def decide(state):
    return strategy.decide(state)
