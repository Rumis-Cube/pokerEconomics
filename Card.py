class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
    def strval(self):
        cardval=f'{self.rank}{self.suit}'
        return cardval
    