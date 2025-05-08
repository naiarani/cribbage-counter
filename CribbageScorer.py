# from itertools import combinations

# # Card pip‐value map for scoring 15s, pegging, etc.
# CARD_VALUES = {
#     'Ace':   1,
#     'Two':   2,
#     'Three': 3,
#     'Four':  4,
#     'Five':  5,
#     'Six':   6,
#     'Seven': 7,
#     'Eight': 8,
#     'Nine':  9,
#     'Ten':  10,
#     'Jack': 10,
#     'Queen':10,
#     'King': 10
# }

# class CribbageScorer:
#     def __init__(self):
#         self.scores = {'Player 1': 0, 'Player 2': 0}
#         self.score_history = []
#         self.pegging_stack = []
#         self.current_total = 0
#         self.turn = None
#         self.first_player = None
#         self.crib_owner = None
#         self.cut_card = None
#         self.game_over = False
#         self.regions = {}

#     def set_first_card_in_crib(self, card_name):
#         # His Heels: if the cut is a Jack, crib owner gets 2 immediately
#         if not self.cut_card:
#             self.cut_card = card_name
#             rank, suit = card_name.split(' of ')
#             if rank == 'Jack' and self.crib_owner:
#                 self.scores[self.crib_owner] += 2
#                 self.score_history.append({
#                     'phase': 'heels',
#                     'player': self.crib_owner,
#                     'delta': 2,
#                     'total': self.scores[self.crib_owner]
#                 })

#     def set_first_player(self, player, crib_owner=None):
#         self.first_player = player
#         if crib_owner:
#             self.crib_owner = crib_owner
#         self.turn = player

#     def _get_rank(self, card_name):
#         return card_name.split()[0]

#     def _get_suit(self, card_name):
#         return card_name.split()[-1]

#     def card_value(self, card_name):
#         return CARD_VALUES.get(self._get_rank(card_name), 0)

#     def switch_turn(self):
#         self.turn = 'Player 2' if self.turn == 'Player 1' else 'Player 1'

#     def score_pegging(self, player, card_name):
#         value = self.card_value(card_name)
#         self.pegging_stack.append(card_name)
#         self.current_total += value

#         score = 0
#         # Fifteen for 2
#         if self.current_total == 15:
#             score += 2
#         # Thirty-one for 2
#         if self.current_total == 31:
#             score += 2
#         # Pairs, triplets, quads
#         n = len(self.pegging_stack)
#         if n >= 2 and self._get_rank(self.pegging_stack[-1]) == self._get_rank(self.pegging_stack[-2]):
#             score += 2
#         if n >= 3 and all(self._get_rank(self.pegging_stack[-1]) == self._get_rank(c)
#                           for c in self.pegging_stack[-3:]):
#             score += 6
#         if n >= 4 and all(self._get_rank(self.pegging_stack[-1]) == self._get_rank(c)
#                           for c in self.pegging_stack[-4:]):
#             score += 12

#         self.scores[player] += score
#         self.score_history.append({
#             'phase': 'pegging',
#             'player': player,
#             'card': card_name,
#             'delta': score,
#             'total': self.scores[player]
#         })

#         self.switch_turn()
#         return score

#     def score_hand(self, cards, cut_card, is_crib=False):
#         hand = cards + [cut_card]
#         score = 0

#         # 15s
#         values = [self.card_value(c) for c in hand]
#         for r in range(2, 6):
#             for combo in combinations(values, r):
#                 if sum(combo) == 15:
#                     score += 2

#         # pairs/triples/quads
#         ranks = [self._get_rank(c) for c in hand]
#         for r in set(ranks):
#             cnt = ranks.count(r)
#             if cnt == 2:
#                 score += 2
#             elif cnt == 3:
#                 score += 6
#             elif cnt == 4:
#                 score += 12

#         # runs
#         order = {'Ace':1,'Two':2,'Three':3,'Four':4,'Five':5,
#                  'Six':6,'Seven':7,'Eight':8,'Nine':9,'Ten':10,
#                  'Jack':11,'Queen':12,'King':13}
#         numeric = sorted(order[r] for r in ranks)
#         for length in range(3, 6):
#             for combo in combinations(numeric, length):
#                 if list(range(min(combo), min(combo)+length)) == sorted(combo):
#                     score += length

#         # His Nobs: Jack in hand matching cut-card suit (only in non-crib hands)
#         if not is_crib:
#             cut_suit = self._get_suit(cut_card)
#             for c in cards:  # only the original 4 cards
#                 if self._get_rank(c) == 'Jack' and self._get_suit(c) == cut_suit:
#                     score += 1
#                     break

#         return score

#     def score_round(self, p1_hand, p2_hand, crib_hand, cut_card):
#         # Player 1 hand
#         p1_delta = self.score_hand(p1_hand, cut_card, is_crib=False)
#         self.scores['Player 1'] += p1_delta
#         self.score_history.append({
#             'phase': 'hand',
#             'player': 'Player 1',
#             'delta': p1_delta,
#             'total': self.scores['Player 1']
#         })

#         # Player 2 hand
#         p2_delta = self.score_hand(p2_hand, cut_card, is_crib=False)
#         self.scores['Player 2'] += p2_delta
#         self.score_history.append({
#             'phase': 'hand',
#             'player': 'Player 2',
#             'delta': p2_delta,
#             'total': self.scores['Player 2']
#         })

#         # Crib
#         if self.crib_owner:
#             crib_delta = self.score_hand(crib_hand, cut_card, is_crib=True)
#             self.scores[self.crib_owner] += crib_delta
#             self.score_history.append({
#                 'phase': 'crib',
#                 'player': self.crib_owner,
#                 'delta': crib_delta,
#                 'total': self.scores[self.crib_owner]
#             })

#     def check_game_over(self, endpoint=121):
#         for p, s in self.scores.items():
#             if s >= endpoint:
#                 self.game_over = True
#                 return p
#         return None

#     def get_scores(self):
#         return dict(self.scores)

#     def get_history(self):
#         return list(self.score_history)


################

# CribbageScorer.py
from itertools import combinations
from collections import Counter

# pip‐value map for 15’s and pegging counts
CARD_VALUES = {
    'Ace':   1, 'Two':   2, 'Three': 3, 'Four':  4,
    'Five':  5, 'Six':   6, 'Seven': 7, 'Eight': 8,
    'Nine':  9, 'Ten':  10, 'Jack': 10, 'Queen':10,
    'King': 10
}

# map ranks to numeric order for runs
RANK_ORDER = {
    'Ace':1, 'Two':2, 'Three':3, 'Four':4, 'Five':5,
    'Six':6, 'Seven':7, 'Eight':8, 'Nine':9, 'Ten':10,
    'Jack':11, 'Queen':12, 'King':13
}

class CribbageScorer:
    def __init__(self):
        # cumulative game scores
        self.scores = {'Player 1': 0, 'Player 2': 0}
        # full history of scoring events
        self.score_history = []
        # pegging state
        self.pegging_stack = []
        self.current_total = 0
        # turn / dealer
        self.turn = None
        self.first_player = None
        self.crib_owner = None
        # cut card
        self.cut_card = None
        # regions (set externally)
        self.regions = {}

    def _get_rank(self, card):
        return card.split()[0]
    def _get_suit(self, card):
        return card.split()[-1]

    def card_value(self, card):
        return CARD_VALUES[self._get_rank(card)]

    def set_first_card_in_crib(self, card_name):
        """Record cut; if it's a Jack, dealer gets 2 points ('heels')."""
        if self.cut_card is None:
            self.cut_card = card_name
            rank, suit = self._get_rank(card_name), self._get_suit(card_name)
            if rank == 'Jack' and self.crib_owner:
                self.scores[self.crib_owner] += 2
                self.score_history.append({
                    'phase': 'heels',
                    'player': self.crib_owner,
                    'delta': 2,
                    'total': self.scores[self.crib_owner]
                })

    def set_first_player(self, first_player, crib_owner):
        """Who leads pegging, who owns the crib."""
        self.first_player = first_player
        self.crib_owner   = crib_owner
        self.turn         = first_player

    def switch_turn(self):
        self.turn = 'Player 2' if self.turn == 'Player 1' else 'Player 1'

    def score_pegging(self, player, card_name):
        """Score a single pegging play, return points scored."""
        v = self.card_value(card_name)
        self.pegging_stack.append(card_name)
        self.current_total += v

        pts = 0
        # 15 and 31
        if self.current_total == 15: pts += 2
        if self.current_total == 31: pts += 2

        # pairs / trips / quads
        n = len(self.pegging_stack)
        if n >= 2 and self._get_rank(self.pegging_stack[-1]) == self._get_rank(self.pegging_stack[-2]):
            pts += 2
        if n >= 3 and all(self._get_rank(self.pegging_stack[-2]) == self._get_rank(c)
                          for c in self.pegging_stack[-3:]):
            pts += 6
        if n >= 4 and all(self._get_rank(self.pegging_stack[-3]) == self._get_rank(c)
                          for c in self.pegging_stack[-4:]):
            pts += 12

        # runs in pegging: check every time?
        # (Optional: implement pegging‐run scoring here.)

        # update
        self.scores[player] += pts
        self.score_history.append({
            'phase': 'pegging',
            'player': player,
            'card': card_name,
            'delta': pts,
            'total': self.scores[player]
        })
        # switch turn
        self.switch_turn()
        return pts

    def score_hand(self, hand_cards, cut_card, is_crib=False):
        """
        Score a five‐card hand (4 + cut) or the crib (4 from crib + cut).
        Returns total points for that hand.
        """
        # build the full 5-card array
        cards = list(hand_cards)
        cards.append(cut_card)
        total = 0

        # 1) Flush
        #    main hand: any 4 same suit +1 if cut matches
        #    crib: only all 5 same suit
        suits = [self._get_suit(c) for c in hand_cards]
        if len(set(suits)) == 1:
            # 4-card flush
            if not is_crib:
                total += 4
                if self._get_suit(cut_card) == suits[0]:
                    total += 1
            else:
                # crib: require cut to match
                if self._get_suit(cut_card) == suits[0]:
                    total += 5

        # 2) Fifteens
        vals = [self.card_value(c) for c in cards]
        for r in range(2, 6):
            for combo in combinations(vals, r):
                if sum(combo) == 15:
                    total += 2

        # 3) Pairs / trips / quads
        ranks = [self._get_rank(c) for c in cards]
        cnt = Counter(ranks)
        for r, n in cnt.items():
            if n == 2:  total += 2
            if n == 3:  total += 6
            if n == 4:  total += 12

        # 4) Runs (including double, triple, etc)
        #    find each maximal run segment in the 5 cards:
        num_counts = Counter(RANK_ORDER[r] for r in ranks)
        unique = sorted(num_counts)
        i = 0
        while i < len(unique):
            # find consecutive block
            j = i+1
            while j < len(unique) and unique[j] == unique[j-1]+1:
                j += 1
            run_vals = unique[i:j]
            L = len(run_vals)
            if L >= 3:
                # multiplicity = product of counts for each rank in run
                mult = 1
                for v in run_vals:
                    mult *= num_counts[v]
                total += L * mult
            i = j

        # 5) Knobs (nobs): a Jack in the hand matching suit of the cut
        if not is_crib:
            cut_suit = self._get_suit(cut_card)
            for c in hand_cards:
                if self._get_rank(c) == 'Jack' and self._get_suit(c) == cut_suit:
                    total += 1
                    break

        return total

    def score_round(self, p1_hand, p2_hand, crib_hand, cut_card):
        """
        After pegging, score both players' hands and the crib.
        Records each sub‐phase in history.
        """
        # Player 1
        d1 = self.score_hand(p1_hand, cut_card, is_crib=False)
        self.scores['Player 1'] += d1
        self.score_history.append({
            'phase': 'hand',
            'player': 'Player 1',
            'delta': d1,
            'total': self.scores['Player 1']
        })

        # Player 2
        d2 = self.score_hand(p2_hand, cut_card, is_crib=False)
        self.scores['Player 2'] += d2
        self.score_history.append({
            'phase': 'hand',
            'player': 'Player 2',
            'delta': d2,
            'total': self.scores['Player 2']
        })

        # Crib (to dealer)
        if self.crib_owner:
            dc = self.score_hand(crib_hand, cut_card, is_crib=True)
            self.scores[self.crib_owner] += dc
            self.score_history.append({
                'phase': 'crib',
                'player': self.crib_owner,
                'delta': dc,
                'total': self.scores[self.crib_owner]
            })

    def get_scores(self):
        return dict(self.scores)

    def get_history(self):
        return list(self.score_history)
