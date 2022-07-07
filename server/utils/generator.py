# encoding=utf8

# 01) 单张：从3(最小)到大王(最大)；
# 02) 一对：两张大小相同的牌，从3(最小)到2(最大)；
# 03) 三张：三张大小相同的牌；
# 04) 三带一：三张并带上任意一张牌，例如6-6-6-8，根据三张的大小来比较，例如9-9-9-3盖过8-8-8-A；
# 05) 三带一对：三张并带上一对，类似扑克中的副路(Full House)，根据三张的大小来比较，例如Q-Q-Q-6-6盖过10-10-10-K-K；
# 06) 顺子：至少5张连续大小(从3到A，2和王不能用)的牌，例如8-9-10-J-Q；
# 07) 连对：至少3个连续大小(从3到A，2和王不能用)的对子，例如10-10-J-J-Q-Q-K-K；
# 08) 三顺：至少2个连续大小(从3到A)的三张，例如4-4-4-5-5-5；
# 09) 飞机带单：每个三张都带上额外的一个单张，例如7-7-7-8-8-8-3-6，三张2不能用
# 10) 飞机带对：每个三张都带上额外的一对，例如8-8-8-9-9-9-4-4-J-J，三张2不能用
# 11) 炸弹：四张大小相同的牌，炸弹能盖过除火箭外的其他牌型，大的炸弹能盖过小的炸弹；
# 12) 火箭：一对王，这是最大的组合，能够盖过包括炸弹在内的任何牌型；
# 13) 四带二单：一个四张带上两个单张，例如6-6-6-6-8-9
# 14) 四带二对：一个四张带上两对，例如 J-J-J-J-9-9-Q-Q

# ♠ ♡ ♢ ♣
from collections import OrderedDict
from itertools import combinations
from typing import Dict, List

CARDS = '34567890JQKA2'


def generate_seq(num: int, seq_db: List[str]) -> List[str]:
    seq = []
    for idx, s in enumerate(seq_db):
        if idx + num > 12:
            break
        seq.append(''.join(seq_db[idx:idx + num]))
    return seq


def sort_cards(cards: str) -> str:
    c = sorted(cards, key=lambda card: '34567890JQKA2wW'.find(card))
    if '33334445556667778888' == ''.join(c):
        print(c)
    return ''.join(c)


def generate_trio_append_single(seq_trio: str, rule: Dict[str, List[str]], num: int) -> List[str]:
    seq_trio_single = []

    comb_single = [single for single in rule['single'] if single not in seq_trio]
    comb_pair = [pair for pair in rule['pair'] if pair not in seq_trio]

    population = [(num - i * 2, i) for i in range(0, num // 2 + 1)]
    for num_1, num_2 in population:
        for single in combinations(comb_single, num_1) or ['']:
            if 'w' in single and 'W' in single:
                continue
            for pair in combinations(comb_pair, num_2) or ['']:
                if single in pair:
                    continue
                seq_trio_single.append(sort_cards(seq_trio + ''.join(single) + ''.join(pair)))

    if num == 4:
        for bomb in [bomb for bomb in rule['bomb'] if bomb[0] not in seq_trio]:
            seq_trio_single.append(sort_cards(seq_trio + ''.join(bomb)))
    elif num == 5:
        for single in comb_single:
            for bomb in [bomb for bomb in rule['bomb'] if bomb[0] not in seq_trio]:
                if single in bomb:
                    continue
                seq_trio_single.append(sort_cards(seq_trio + ''.join(single) + ''.join(bomb)))

    return seq_trio_single


def generate_trio_append_pair(seq_trio: str, rule: Dict[str, List[str]], num: int) -> List[str]:
    seq_trio_pair = []

    population = [(num - i * 2, i) for i in range(0, num // 2 + 1)]
    com_pair = [pair for pair in rule['pair'] if pair not in seq_trio]
    com_bomb = [bomb for bomb in rule['bomb'] if bomb[0] not in seq_trio]

    for num_1, num_2 in population:
        for pair in combinations(com_pair, num_1) or ['']:
            for bomb in combinations(com_bomb, num_2) or ['']:
                seq_trio_pair.append(sort_cards(seq_trio + ''.join(pair) + ''.join(bomb)))

    return seq_trio_pair


def generate():
    rule = OrderedDict()
    rule['single'] = [c for c in CARDS]
    rule['pair'] = [c * 2 for c in CARDS]
    rule['trio'] = [c * 3 for c in CARDS]
    rule['bomb'] = [c * 4 for c in CARDS]
    rule['rocket'] = ['wW']

    for num in [5, 6, 7, 8, 9, 10, 11, 12]:
        rule[f'seq_single{num}'] = generate_seq(num, rule['single'])
    for num in [3, 4, 5, 6, 7, 8, 9, 10]:
        rule[f'seq_pair{num}'] = generate_seq(num, rule['pair'])
    for num in [2, 3, 4, 5, 6]:
        rule[f'seq_trio{num}'] = generate_seq(num, rule['trio'])

    rule['single'].append('w')
    rule['single'].append('W')

    rule['trio_single'] = []
    rule['trio_pair'] = []
    for trio in rule['trio']:
        rule['trio_single'] += [sort_cards(trio + single) for single in rule['single'] if single != trio[0]]
        rule['trio_pair'] += [sort_cards(trio + p) for p in rule['pair'] if p[0] != trio[0]]

    for num in [2, 3, 4, 5]:
        rule[f'seq_trio_single{num}'] = []
        rule[f'seq_trio_pair{num}'] = []
        for seq_trio in rule[f'seq_trio{num}']:
            rule[f'seq_trio_single{num}'] += generate_trio_append_single(seq_trio, rule, num)
            rule[f'seq_trio_pair{num}'] += generate_trio_append_pair(seq_trio, rule, num)

    rule['bomb_single'] = []
    rule['bomb_pair'] = []
    for b in rule['bomb']:
        seq = [single for single in rule['single'] if single not in b]
        for comb in combinations(seq, 2):
            if 'w' in comb and 'W' in comb:
                continue
            comb = ''.join(comb)
            rule['bomb_single'].append(sort_cards(b + comb))
            if 'w' in comb or 'W' in comb:
                continue
            rule['bomb_pair'].append(sort_cards(b + comb[0] + comb[0] + comb[1] + comb[1]))

    del rule['seq_trio_pair5']

    for name, specs_list in rule.items():
        assert isinstance(specs_list[0], str)
        print(f'{name:>16}{len(specs_list[0]): >4}{len(specs_list): >6}')

    print('-' * 26)
    print('{:>16}{:>10}'.format('Total', sum(map(len, rule.values()))))
    return rule


def main():
    import json
    with open('rule.json', 'w') as out:
        json.dump(generate(), out, indent=4)


if __name__ == '__main__':
    main()
