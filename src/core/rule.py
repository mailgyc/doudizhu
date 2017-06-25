from collections import Counter
import json

CARD_TYPES = [
    # 'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11',
    'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4', 'seq_trio_pair5',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'
]

with open('static/rule.json', 'r') as f:
    ruleList = json.load(f)


def sort_card(a):
    return '34567890JQKA2wW'.index(a)


def to_cards(pokers):
    cards = []
    for p in pokers:
        if p == 52:
            cards.append('W')
        elif p == 53:
            cards.append('w')
        else:
            cards.append('A234567890JQK'[p % 13])
    return cards


def cards_value(cards):
    def find(array, ele):
        if len(array[0]) != len(ele):
            return -1
        for i, e in enumerate(array):
            if e == ele:
                return i
        return -1

    if isinstance(cards, list):
        cards = to_cards(cards)
    cards = ''.join(sorted(cards, key=sort_card))

    if cards == 'wW':
        return 'rocket', 2000

    value = find(ruleList['bomb'], cards)
    if value >= 0:
        return 'bomb', 1000 + value

    for t in CARD_TYPES:
        value = find(ruleList[t], cards)
        if value >= 0:
            return t, value

    return '', 0


def cards_above(hand_cards, turn_cards):
    pair = cards_value(turn_cards)
    if pair[0] == '':
        return ''

    hand_cards = sorted(hand_cards, keys=sort_card)
    one_rule = ruleList[pair[0]]
    for i, t in enumerate(one_rule):
        if i > pair[1] and is_contains(hand_cards, t):
            return t

    if pair[1] < 1000:
        one_rule = ruleList['bomb']
        for t in one_rule:
            if is_contains(hand_cards, t):
                return t
        if is_contains(hand_cards, 'wW'):
            return 'wW'
    return ''


def compare(cards_a, cards_b):
    value_a = cards_value(cards_a)
    if value_a[0] == '':
        return -10000

    value_b = cards_value(cards_b)
    if value_a[0] == value_b[0]:
        return value_a[1] - value_b[1]

    if value_a[1] >= 1000:
        return value_a[1] - value_b[1]
    else:
        return 0


def is_contains(parent, child):
    parent, child = Counter(parent), Counter(child)
    for k, n in child.items():
        if k not in parent or n > parent[k]:
            return False
    return True


if __name__ == '__main__':
    print('compare("AAAK", "5552")', compare('AAAK', '5552'))
    print('cardsValue("AAAA")', cards_value('AAAA'))
