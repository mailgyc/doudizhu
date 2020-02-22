import json
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Iterable, Optional

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
        self.cnt_to_specs: Dict[int, List[str]] = defaultdict(list)
        for name, specs_list in rules.items():
            self.cnt_to_specs[len(specs_list[0])].append(name)

    def get_poker_spec(self, pokers: List[int]) -> Optional[str]:
        cards = ''.join(self._to_cards(pokers))
        for spec in self.cnt_to_specs.get(len(cards), []):
            if cards in self.rules[spec]:
                return spec
        return None

    def find_best_shot(self, hand_pokers: List[int]) -> List[int]:
        hand_cards = self._to_cards(hand_pokers)
        best_shot = self._find_best_shot(hand_cards)
        return self._to_pokers(hand_pokers, best_shot)

    def _find_best_shot(self, hand_cards: List[str]) -> str:
        for spec in self.cnt_to_specs.get(len(hand_cards), []):
            if spec == 'bomb_single' or spec == 'bomb_pair':
                continue
            results, available = self.find_spec_type(hand_cards, spec)
            if not available:
                return results[0]

        rockets, available = self.find_spec_type(hand_cards, 'rocket')
        bombs, available = self.find_spec_type(available, 'bomb')

        small_cards, bigger_cards = self.split_cards(available)
        total_single = self.count_single(small_cards)

        for n in [12, 11, 10, 9, 8, 7, 6, 5]:
            seq_single, after_cards = self.find_spec_type(small_cards, f'seq_single{n}')
            after_single = self.count_single(after_cards)
            if total_single - after_single > 2:
                longer_seq_list, after_cards = self.expand_seq(seq_single, bigger_cards)
                if after_single - self.count_single(after_cards) > len(longer_seq_list[0]) - len(seq_single[0]):
                    return longer_seq_list[0]
                return seq_single[0]

        for spec in ['seq_trio_single4', 'seq_trio_single3', 'seq_trio_single2', 'trio_single']:
            seq_trio, after_cards = self.find_spec_type(small_cards, spec)
            if seq_trio and self.count_single(after_cards) < total_single:
                return seq_trio[0]

        for spec in ['seq_trio_pair3', 'seq_trio_pair2', 'trio_pair']:
            seq_trio, after_cards = self.find_spec_type(small_cards, spec)
            if seq_trio and self.count_single(after_cards) <= total_single:
                return seq_trio[0]

        for spec in ['seq_pair9', 'seq_pair8', 'seq_pair7', 'seq_pair6', 'seq_pair5', 'seq_pair4', 'seq_pair3']:
            seq_pair, after_cards = self.find_spec_type(small_cards, spec)
            if seq_pair and self.count_single(after_cards) < total_single:
                return seq_trio[0]

        for spec in ['pair', 'trio', 'single']:
            pair, after_cards = self.find_spec_type(small_cards, spec)
            if pair and self.count_single(after_cards) <= total_single:
                return pair[0]

        return hand_cards[0]

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

    def _expand_seq_multiple(self, seq: str, available: List[str]) -> Tuple[str, List[str]]:
        while len(available) > 0:
            size = len(available)
            seq, available = self._expand_seq_once(seq, available)
            if len(available) == size:
                break
        return seq, available

    def _expand_seq_once(self, seq: str, available: List[str]) -> Tuple[str, List[str]]:
        spec = f'seq_single{len(seq) + 1}'
        if spec not in self.rules:
            return seq, available

        for card in available:
            if self._index_of(self.rules[spec], seq + card) < 0:
                continue
            available.remove(card)
            return seq + card, available
        return seq, available

    def cards_above(self, hand_pokers: List[int], turn_pokers: List[int], follow=True) -> List[int]:
        hand_cards = self._to_cards(hand_pokers)
        turn_cards = self._to_cards(turn_pokers)

        card_type, card_value = self._get_cards_value(turn_cards)
        if not card_type:
            return []

        if follow and card_type not in ['single', 'pair', 'trio_single', 'trio_pair', 'seq_single5']:
            return []

        for i, spec in enumerate(self.rules[card_type]):
            if i > card_value and self.is_contains(hand_cards, spec):
                if follow and i*1.0/len(self.rules[card_type]) > 0.8:
                    return []
                cards = self._to_pokers(hand_pokers, spec)
                return cards

        if follow:
            return []

        if card_value < 10000:
            for spec in self.rules['bomb']:
                if self.is_contains(hand_cards, spec):
                    return self._to_pokers(hand_pokers, spec)
            if self.is_contains(hand_cards, 'wW'):
                return [53, 54]
        return []

    def compare_pokers(self, a_pokers, b_pokers) -> int:
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

        if a_card_value >= 10000:
            return 1
        else:
            return 0

    def _get_cards_value(self, cards: List[str]) -> Tuple[str, int]:
        cards = ''.join(cards)
        if cards == 'wW':
            return 'rocket', 20000

        value = self._index_of(self.rules['bomb'], cards)
        if value >= 0:
            return 'bomb', 10000 + value

        return self._get_card_value(cards)

    def _get_card_value(self, cards: str) -> Tuple[str, int]:
        specs = self.cnt_to_specs.get(len(cards), [])
        for spec in specs:
            value = self._index_of(self.rules[spec], cards)
            if value >= 0:
                return spec, value
        logging.error('Unknown Card Type: %s', cards)
        return '', 0

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
    def _to_pokers(hand_pokers: List[int], cards: Iterable) -> List[int]:
        pokers = []
        for card in cards:
            candidates = Rule._to_poker(card)
            for cd in candidates:
                if cd in hand_pokers and cd not in pokers:
                    pokers.append(cd)
                    break
        return pokers

    @staticmethod
    def split_cards(hand_cards: List[str]) -> Tuple[List[str], List[str]]:
        return [c for c in hand_cards if c not in 'A2wW'], [c for c in hand_cards if c in 'A2wW']

    @staticmethod
    def count_single(hand_cards: List[str]) -> int:
        return sum(v for _, v in Counter(hand_cards).items() if v == 1)

    @staticmethod
    def _index_of(array: List[str], ele: str) -> int:
        if len(array[0]) != len(ele):
            return -1
        try:
            return array.index(ele)
        except ValueError:
            return -1

    @staticmethod
    def is_contains(parent: Iterable, child: Iterable) -> bool:
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
    # from random import sample
    # print(rule._find_best_shot('345677890JQQKAAA2'))
    # print(rule._find_best_shot('34456788990JJQKAW'))
    # print(rule._find_best_shot('3344555678990JQKK'))
    #
    # rnd = sample(list(range(1, 55)), k=17)
    # print(''.join(rule._to_cards(rnd)), ''.join(rule._to_cards(rule.find_best_shot(rnd))))
