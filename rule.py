from collections import Counter
import json

cardsType = [
    #'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11', 'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4', 'seq_trio_pair5',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'
]

with open('static/assets/rule.json', 'r') as f:
    ruleList = json.load(f)

def sortfunc(a):
    return '34567890JQKA2wW'.index(a)

def cardsValue(cards):

    def find(array, ele):
        if len(array[0]) != len(ele):
            return -1
        for i, e in enumerate(array):
            if e == ele:
                return i
        return -1

    cards = ''.join(sorted(cards, key=sortfunc))

    if cards == 'wW':
        return ('rocket', 2000)

    value = find(ruleList['bomb'], cards)
    if value >= 0:
        return ('bomb', 1000 + value)

    for t in cardsType:
        value = find(ruleList[t], cards)
        if value >= 0:
            return (t, value)

    return ('', 0)

def cardsAbove(handCards, turnCards):
    pair = cardsValue(turnCards)
    if pair[0] == '':
        return ''

    handCards = sorted(handCards, keys=sortfunc)
    oneRule = ruleList[pair[0]]
    for i, t in enumerate(oneRule):
        if i > pair[1] and containsAll(handCards, t):
            return t

    if pair[1] < 1000:
        oneRule = ruleList['bomb']
        for t in oneRule:
            if containsAll(handCards, t):
                return t
        if containsAll(handCards, 'wW'):
            return 'wW'
    return ''

def compare(cardsA, cardsB):
    valueA = cardsValue(cardsA)
    if valueA[0] == '':
        return -10000

    valueB = cardsValue(cardsB)
    if valueA[0] == valueB[0]:
        return valueA[1] - valueB[1]

    if valueA[1] >= 1000:
        return valueA[1] - valueB[1]
    else:
        return 0

def containsAll(parent, child):
    parent, child = Counter(parent), Counter(child)
    for k, n in child.items():
        if k not in parent or n > parent[k]:
            return False
    return True

if __name__ == '__main__':
    print('compare("AAAK", "5552")', compare('AAAK', '5552'))
    print('cardsValue("AAAA")', cardsValue('AAAA'))



