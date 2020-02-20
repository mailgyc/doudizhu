import json
import logging
from collections import Counter
from typing import Dict, List, Tuple

'''
# A 2 3 4 5 6 7 8 9 0 J Q K w W
'''

CARD_TYPES = [
    'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11',
    'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'
]


class Rule(object):

    def __init__(self, rules: Dict[str, List[str]]):
        self.rules = rules

    def analysis(self, hand_pokers: List[int]):
        hand_cards = self._to_cards(hand_pokers)

        # 1. 选取单顺
        # seq_single5_list, available = self.find_spec_type(hand_cards, 'seq_single5')

        # 2. 扩展单顺
        # longer_seq_list, available = self.expand_seq(seq_single5_list, available)

        # 3. 合并单顺
        # longer_seq_list, available = self.merge_seq()

    def find_spec_type(self, hand_cards: List[str], card_type: str) -> Tuple[List[str], List[str]]:
        available = [c for c in hand_cards]
        result = []
        for spec in self.rules[card_type]:
            if self.is_contains(available, spec):
                for sp in spec:
                    available.remove(sp)
                result.append(spec)

        return result, available

    def expand_seq(self, seq_list: List[str], available: List[str]) -> Tuple[List[str], List[str]]:
        longer_seq_list = []
        for idx, seq in enumerate(seq_list):
            longer_seq, available = self._expand_seq_multiple(seq, available)
            longer_seq_list.append(longer_seq)
        return longer_seq_list, available

    def merge_seq(self, seq_list: List[str]) -> List[str]:
        pass

    def _expand_seq_multiple(self, seq: str, available: List[str]) -> Tuple[str, List[str]]:
        longer_seq = seq
        while len(available) > 0:
            longer_seq, available = self._expand_seq_once(longer_seq, available)
            if longer_seq == seq:
                break
        return longer_seq, available

    def _expand_seq_once(self, seq: str, available: List[str]) -> Tuple[str, List[str]]:
        no = len(seq) + 1
        for card in available:
            if self._index_of(self.rules[f'seq_single{no}'], seq + card) >= 0:
                available.remove(card)
                return seq + card, available
        return seq, available

    def cards_above(self, hand_pokers: List[int], turn_pokers: List[int]) -> List[int]:
        hand_cards = self._to_cards(hand_pokers)
        turn_cards = self._to_cards(turn_pokers)

        card_type, card_value = self._get_cards_value(turn_cards)
        if not card_type:
            return []

        specs = self.rules[card_type]
        for i, spec in enumerate(specs):
            if i > card_value and self.is_contains(hand_cards, spec):
                return self._to_pokers(hand_pokers, spec)

        if card_value < 1000:
            specs = self.rules['bomb']
            for spec in specs:
                if self.is_contains(hand_cards, spec):
                    return self._to_pokers(hand_pokers, spec)
            if self.is_contains(hand_cards, 'wW'):
                return [53, 54]
        return []

    def compare_poker(self, a_pokers, b_pokers) -> int:
        if not a_pokers or not b_pokers:
            if a_pokers == b_pokers:
                return 0
            if a_pokers:
                return 1
            if b_pokers:
                return 1

        a_card_type, a_card_value = self._get_cards_value(self._to_cards(a_pokers))
        b_card_type, b_card_value = self._get_cards_value(self._to_cards(b_pokers))
        if a_card_type == b_card_type:
            return a_card_value - b_card_value

        if a_card_value >= 1000:
            return 1
        else:
            return 0

    @staticmethod
    def _to_cards(pokers) -> List[str]:
        cards = []
        for p in pokers:
            if p == 53:
                cards.append('w')
            elif p == 54:
                cards.append('W')
            else:
                cards.append('KA234567890JQ'[p % 13])
        return Rule._sort_card(cards)

    @staticmethod
    def _to_poker(card: str) -> List[int]:
        if card == 'w':
            return [53]
        if card == 'W':
            return [54]

        cards = '?A234567890JQK'
        for i, c in enumerate(cards):
            if c == card:
                return [i, i + 13, i + 26, i + 39]
        return [55]

    @staticmethod
    def _to_pokers(hand_pokers: List[int], cards: str) -> List[int]:
        pokers = []
        for card in cards:
            candidates = Rule._to_poker(card)
            for cd in candidates:
                if cd in hand_pokers and cd not in pokers:
                    pokers.append(cd)
                    break
        return pokers

    def _get_cards_value(self, cards: List[str]) -> Tuple[str, int]:
        cards = ''.join(cards)
        if cards == 'wW':
            return 'rocket', 2000

        value = self._index_of(self.rules['bomb'], cards)
        if value >= 0:
            return 'bomb', 1000 + value

        return self._get_card_value(cards)

    def _get_card_value(self, cards: str) -> Tuple[str, int]:
        for t in CARD_TYPES:
            value = self._index_of(self.rules[t], cards)
            if value >= 0:
                return t, value
        logging.error('Unknown Card Type: %s', cards)
        return '', 0

    @staticmethod
    def _index_of(array: List[str], ele: str) -> int:
        if len(array[0]) != len(ele):
            return -1
        try:
            return array.index(ele)
        except ValueError:
            return -1

    @staticmethod
    def is_contains(parent: List[str], child: str) -> bool:
        parent, child = Counter(parent), Counter(child)
        for k, cnt in child.items():
            if k not in parent or cnt > parent[k]:
                return False
        return True

    @staticmethod
    def _sort_card(cards: List[str]):
        cards.sort(key=lambda ch: '34567890JQKA2wW'.index(ch))
        return cards


with open('static/rule.json', 'r') as f:
    rule = Rule(json.load(f))
