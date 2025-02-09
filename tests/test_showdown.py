import json

from components.Deck import Deck
from components.Player import Player
from components.Showdown import Showdown

deck = Deck()
deck.shuffle()

players={}
with open('players.json','r') as f:
    players=json.load(f)

# Create players
player1 = Player(players['player1']['name'], players['player1']['bankroll'])
player2 = Player(players['player2']['name'], players['player2']['bankroll'])

for i in range(2):
    player1.receive_card(deck.deal_card())
    player2.receive_card(deck.deal_card())

print(player1.hand)
print(player2.hand)

cc = []
for _ in range(5):
    cc.append(str(deck.deal_card()))

print(cc)
s = Showdown(cc, player1, player2)
print(s)
print(s.winner())