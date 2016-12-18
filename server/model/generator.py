# encoding=utf8

# 1) 单张：前面提到过，大小顺序从3(最小)到大怪(最大)；
# 2) 一对：两张大小相同的牌，从3(最小)到2(最大)；
# 3) 三张：三张大小相同的牌；
# 4) 三张带一张：三张并带上任意一张牌，例如6-6-6-8，根据三张的大小来比较，例如9-9-9-3盖过8-8-8-A；
# 5) 三张带一对：三张并带上一对，类似扑克中的副路(Full House)，根据三张的大小来比较，例如Q-Q-Q-6-6盖过10-10-10-K-K；
# 6) 顺子：至少5张连续大小(从3到A，2和怪不能用)的牌，例如8-9-10-J-Q；
# 7) 连对：至少3个连续大小(从3到A，2和怪不能用)的对子，例如10-10-J-J-Q-Q-K-K；
# 8) 三张的顺子：至少2个连续大小(从3到A)的三张，例如4-4-4-5-5-5；
# 9) 三张带一张的顺子：每个三张都带上额外的一个单张，例如7-7-7-8-8-8-3-6，尽管三张2不能用，但能够带上单张2和怪；
# 10) 三张带一对的顺子：每个三张都带上额外的一对，例如8-8-8-9-9-9-4-4-J-J，尽管三张2不能用，但能够带上一对2，三张带上的单张和一对不能是混合的，例如3-3-3-4-4-4-6-7-7就是不合法的；
# 11) 炸弹：四张大小相同的牌，炸弹能盖过除火箭外的其他牌型，大的炸弹能盖过小的炸弹；
# 12) 火箭：一对怪，这是最大的组合，能够盖过包括炸弹在内的任何牌型；
# 13) 四张套路(四带二)：有两种牌型，一个四张带上两个单张，例如6-6-6-6-8-9，或一个四张带上两对，例如J-J-J-J-9-9-Q-Q，四张带二张和四张带二对属于不同的牌型，不能彼此盖过;

cards = '34567890JQKA2'
rule = {}


def generateASeq(num, seqDB):
    seq = []
    for idx, s in enumerate(seqDB):
        if idx + num > 12:
            break
        seq.append(''.join(seqDB[idx:idx + num]))
    return seq


def generateSeq(allowSeq, seqDB):
    ret = []
    for size in allowSeq:
        seq = generateASeq(size, seqDB)
        if seq:
            ret.append(seq)
    return ret


def combination(seq, k):
    if k == 0:
        print('error: ', 0)
        return []
    if len(seq) < k:
        print('error: ', seq, k)
        return []
    if k == 1:
        return [[s] for s in seq]
    if len(seq) == k:
        return [seq]
    noFirst = combination(seq[1:], k)
    hasFirst = map(lambda sub: [seq[0]] + sub, combination(seq[1:], k - 1))
    return noFirst + list(hasFirst)


def permutation(seq):
    if len(seq) == 1:
        return [seq]
    all = []
    for idx, s in enumerate(seq):
        # for m in permutation(seq[0:idx]+seq[idx+1:]):
        #    all.append([s] + m)
        m = map(lambda sub: [s] + sub, permutation(seq[0:idx] + seq[idx + 1:]))
        all.extend(list(m))
    return all


def sort_cards(cards):
    c = sorted(cards, key=lambda card: '34567890JQKA2Ww'.find(card))
    return ''.join(c)


def generate():
    rule['single'] = []
    rule['pair'] = []
    rule['trio'] = []
    rule['bomb'] = []
    for c in cards:
        rule['single'].append(c)
        rule['pair'].append(c + c)
        rule['trio'].append(c + c + c)
        rule['bomb'].append(c + c + c + c)

    # rule['seq_single'] = generateSeq([5, 6, 7, 8, 9, 10, 11, 12], rule['single'])
    # rule['seq_pair'] = generateSeq([3, 4, 5, 6, 7, 8, 9, 10], rule['pair'])
    # rule['seq_trio'] = generateSeq([2, 3, 4, 5, 6], rule['trio'])
    # rule['seq_bomb'] = generateSeq([2, 3, 4, 5], rule['bomb'])

    for num in [5, 6, 7, 8, 9, 10, 11, 12]:
        rule['seq_single' + str(num)] = generateASeq(num, rule['single'])
    for num in [3, 4, 5, 6, 7, 8, 9, 10]:
        rule['seq_pair' + str(num)] = generateASeq(num, rule['pair'])
    for num in [2, 3, 4, 5, 6]:
        rule['seq_trio' + str(num)] = generateASeq(num, rule['trio'])

    rule['single'].append('w')
    rule['single'].append('W')
    rule['rocket'] = ['Ww']

    rule['trio_single'] = []
    rule['trio_pair'] = []
    for t in rule['trio']:
        for s in rule['single']:
            if s != t[0]:
                rule['trio_single'].append(sort_cards(t + s))
        for p in rule['pair']:
            if p[0] != t[0]:
                rule['trio_pair'].append(sort_cards(t + p))

    # rule['seq_trio_single'] = []
    # rule['seq_trio_pair'] = []
    for num in [2, 3, 4, 5]:
        seq_trio_single = []
        seq_trio_pair = []
        for seq_trio in rule['seq_trio' + str(num)]:
            seq = rule['single'].copy()
            for i in range(0, len(seq_trio), 3):
                seq.remove(seq_trio[i])
            for single in combination(seq, len(seq_trio) / 3):
                single = ''.join(single)
                seq_trio_single.append(sort_cards(seq_trio + single))
                if 'w' not in single and 'W' not in single:
                    pair = ''.join([s + s for s in single])
                    seq_trio_pair.append(sort_cards(seq_trio + pair))
        rule['seq_trio_single' + str(num)] = seq_trio_single
        rule['seq_trio_pair' + str(num)] = seq_trio_pair

    rule['bomb_single'] = []
    rule['bomb_pair'] = []
    for b in rule['bomb']:
        seq = rule['single'].copy()
        seq.remove(b[0])
        for comb in combination(seq, 2):
            comb = ''.join(comb)
            rule['bomb_single'].append(sort_cards(b + comb))
            if 'w' not in comb and 'W' not in comb:
                rule['bomb_pair'].append(sort_cards(b + comb[0] + comb[0] + comb[1] + comb[1]))

    def howmany(v):
        count = 0
        for i in v:
            if isinstance(i, str):
                count += 1
            else:
                count += howmany(i)
        return count

    count = 0
    keys = []
    for k, v in rule.items():
        keys.append(k)
        # count += howmany(v)
        count += len(v)
        if not isinstance(v[0], str):
            print(v)
    keys.sort()
    print(len(keys), keys)
    print(count)


if __name__ == '__main__':
    generate()
    import json

    with open('rule.json', 'w') as out:
        # json.dump(rule, out, sort_keys=True, indent=4)
        json.dump(rule, out)
