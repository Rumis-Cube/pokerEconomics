from Deck import Deck
from Showdown import Showdown
class Game:
    def __init__(self, players):
        self.deck = Deck()
        self.deck.shuffle()
        self.pot = 0
        self.players = players
        self.number_of_players = len(players)
        self.community_cards=[]
        #counts the number of players currently in a game [later gets flushed]
        self.playing=len(players)
    def flush(self):
        self.deck.flush()
        for player in self.players:
            player.flush()
        self.community_cards = []
        self.playing=len(self.players)


    def play(self, number_of_hands):
        for _ in range(number_of_hands):
            self.preflop()
            self.flush()
            # rotates the dealer
            self.players = self.players[-1:] + self.players[:-1]
            self.pot = 0

    # increments the pot by the bet amount whenever a player bets'
    def player_bet(self, player, amt):
        self.pot += player.bet(amt - player.betamt)
                        
    def betting(self, players, betsize):
        # the last player where the action finishes
        end = self.playing - 1

        i = 0

        print(f"pot -> {self.pot}")
        while 1:
            player = players[i % len(players)]

            callsize = betsize - player.betamt

            # check if the player is still in the current game 
            if player.ingame == 0:
                i = (i+1) % len(players)
                continue

            action = input(f"{player.name}'s action -> call(c) / check(ch) / bet(b) / raise(r) / fold(f): ")
            
            if action == "c":
                if callsize != 0:
                    self.player_bet(player, betsize)
                else:
                    print("Illegal move")
                    i = (i+len(players)) % len(players)
                    continue
            
            elif action == "ch":
                if callsize == 0:
                    self.player_bet(player, betsize)
                else:
                    print("Illegal move")
                    i = (i+len(players)) % len(players)
                    continue

            elif action == "b":        
                if betsize == 0:   
                    betsize = player.betamt + int(input(f"Enter the betsize: "))
                    self.player_bet(player, betsize)
                    end = (i-1) % len(players)
                else:
                    print("Illegal move")
                    i = (i+len(players)) % len(players)
                    continue

            elif action == "r":
                if betsize > 0:
                    betsize = player.betamt + int(input(f"Enter the raise: "))
                    self.player_bet(player, betsize)
                    end = (i-1) % len(players) # sets the loop to end on player before this
                else:
                    print("Illegal move")
                    i = (i+len(players)) % len(players)
                    continue

            elif action == "f":
                player.ingame = 0
                self.playing -= 1
                if self.playing == 1:
                    for player in players:
                        if player.ingame == 1:
                            player.bankroll += self.pot
                    self.gameover()
                    return 0
                if i == end:
                    end=(i-1) % len(players)
                    print(f"end is -> {end}")
                    break
            else:
                print("invalid Input")
                i = (i+len(players)) % len(players)
                continue
            # if there is only one person playing then gameover
            if self.playing == 1:
                for player in players:
                    if player.ingame == 1:
                        player.bankroll += self.pot
                self.gameover()
                return 0
            # exit condtion for the loop when all the players have called
            if i == end:
                break
            i = (i+1) % len(players)
            

    #handles the preflop action
    def preflop(self):
        print("-------PRE-FLOP------")
        for i in range(self.number_of_players):
            self.players[i].receive_card(self.deck.deal_card())
            self.players[i].receive_card(self.deck.deal_card())


        bet_size = 2

        #blinds 
        if len(self.players) > 2:
            self.player_bet(self.players[1%len(self.players)], 1)
            self.player_bet(self.players[2%len(self.players)], 2)
        else:
            self.player_bet(self.players[0], 1)
            self.player_bet(self.players[1], 2)

        print("----BLINDS-----")
        for player in self.players:
            print(f"{player.name}'s blind -> {player.betamt}")


        #printing the cards:
        for i in range(self.number_of_players):
            print(f"{self.players[i].name}'s cards")
            for card in self.players[i].hand:
                print(card, end=" ")
            print()

        if self.betting(self.players, bet_size) != 0:
            self.flop()

    def flop(self):
        print("-------FLOP------")

        bet_size = 0

        #resetting the betamts
        for player in self.players:
            player.betamt=0

        #displaying the flop
        for i in range(3):
            self.community_cards.append(str(self.deck.deal_card()))
        
        print(self.community_cards) 

        if self.betting(self.players, bet_size) != 0:
            self.turn()
        


    def turn(self):
        print("-------TURN------")
        bet_size = 0
        
        #resetting the betamts
        for player in self.players:
            player.betamt=0

        self.community_cards.append(str(self.deck.deal_card()))
        
        print(self.community_cards)

        if self.betting(self.players, bet_size) != 0:
            self.river()

    def river(self):
        print("-------RIVER------")
        bet_size = 0
        
        #resetting the betamts
        for player in self.players:
            player.betamt=0

        self.community_cards.append(str(self.deck.deal_card()))
        
        print(self.community_cards)

        if self.betting(self.players, bet_size) != 0:
            self.showdown(self.players)

     #displays info at the end of a hand
    def gameover(self):
        print("Hand Ended")
        for i in range(self.number_of_players):
            print(f'{self.players[i].name} stack: {self.players[i].bankroll}')
    
    #showdown
    def showdown(self, players):
        s = Showdown(self.community_cards, players)
        winner = players[s.winner()]
        winner.bankroll += self.pot
        print(f"winner: {winner.name}")
        self.gameover()