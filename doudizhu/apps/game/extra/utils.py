import time
from collections import Counter
from contextlib import contextmanager

import numpy as np
import tensorflow as tf

from apps.game.extra import card
from .card import action_space, Card, Category, action_space_category

action_space_single = action_space[1:16]
action_space_pair = action_space[16:29]
action_space_triple = action_space[29:42]
action_space_quadric = action_space[42:55]


##################################################### UTILITIES ########################################################
def counter_subset(list1, list2):
    c1, c2 = Counter(list1), Counter(list2)

    for (k, n) in c1.items():
        if n > c2[k]:
            return False
    return True


# map char cards to 3 - 17
def to_value(cards):
    if isinstance(cards, list) or isinstance(cards, np.ndarray):
        values = [Card.cards.index(c) + 3 for c in cards]
        return values
    else:
        return Card.cards.index(cards) + 3


# map 3 - 17 to char cards
def to_char(cards):
    if isinstance(cards, list) or isinstance(cards, np.ndarray):
        if len(cards) == 0:
            return []
        chars = [card.Card.cards[c - 3] for c in cards]
        return chars
    else:
        return card.Card.cards[cards - 3]


def get_mask(cards, action_space, last_cards=None):
    # 1 valid; 0 invalid
    mask = np.zeros([len(action_space)])
    if cards is None:
        return mask
    if len(cards) == 0:
        return mask
    for j in range(mask.size):
        if counter_subset(action_space[j], cards):
            mask[j] = 1
    # mask = mask.astype(bool)
    if last_cards is None:
        return mask
    if len(last_cards) > 0:
        for j in range(1, mask.size):
            if mask[j] == 1 and not card.CardGroup.to_cardgroup(action_space[j]). \
                    bigger_than(card.CardGroup.to_cardgroup(last_cards)):
                mask[j] = 0
    # else:
    #     mask[0] = False
    return mask


def get_mask_onehot60(cards, action_space, last_cards):
    # 1 valid; 0 invalid
    mask = np.zeros([len(action_space), 60])
    if cards is None:
        return mask
    if len(cards) == 0:
        return mask
    for j in range(len(action_space)):
        if counter_subset(action_space[j], cards):
            mask[j] = card.Card.char2onehot60(action_space[j])
    if last_cards is None:
        return mask
    if len(last_cards) > 0:
        for j in range(1, len(action_space)):
            if np.sum(mask[j]) > 0 and not card.CardGroup.to_cardgroup(action_space[j]). \
                    bigger_than(card.CardGroup.to_cardgroup(last_cards)):
                mask[j] = np.zeros([60])
    return mask


# # get char cards, return valid response
# def get_mask_category(cards, action_space, last_cards=None):
#     mask = np.zeros([14]) if last_cards is None else np.zeros([15])
#     for i in range(action_space):
#         if counter_subset(action_space[i], cards):
#             if last_cards is None:
#                 mask[char2value_3_17(action_space[i][0])-3] = 1
#             else:
#                 diff = char2value_3_17(action_space[i][0]) - char2value_3_17(last_cards[0])
#                 if diff > 0:
#                     mask[diff-1] = 1
#     return mask.astype(bool)


def get_seq_length(category, cards_val):
    if category == Category.SINGLE_LINE.value:
        return cards_val.size
    if category == Category.DOUBLE_LINE.value:
        return cards_val.size // 2
    if category == Category.TRIPLE_LINE.value:
        return cards_val.size // 3
    if category == Category.THREE_ONE_LINE.value:
        return cards_val.size // 4
    if category == Category.THREE_TWO_LINE.value:
        return cards_val.size // 5
    return None


# get [-1, 1] minor cards target, input: value cards 3-17
def find_minor_in_three_one(cards):
    if cards[0] == cards[1]:
        return cards[-1]
    else:
        return cards[0]


def find_minor_in_three_two(cards):
    if cards[1] == cards[2]:
        return cards[-1]
    else:
        return cards[0]


def find_minor_in_three_one_line(cards):
    cnt = np.zeros([18])
    for i in range(len(cards)):
        cnt[cards[i]] += 1
    minor = []
    for i in range(3, 18):
        if cnt[i] == 1:
            minor.append(i)
    return np.array(minor)


def find_minor_in_three_two_line(cards):
    cnt = np.zeros([18])
    for i in range(len(cards)):
        cnt[cards[i]] += 1
    minor = []
    for i in range(3, 18):
        if cnt[i] == 2:
            minor.append(i)
    return np.array(minor)


def find_minor_in_four_two(cards):
    cnt = np.zeros([18])
    for i in range(len(cards)):
        cnt[cards[i]] += 1
    minor = []
    for i in range(3, 18):
        if cnt[i] == 1:
            minor.append(i)
    return np.array(minor)


def get_minor_cards(cards, category_idx):
    minor_cards = np.ones([15])
    length = 0
    if category_idx == Category.THREE_ONE.value:
        length = 1
        minor_cards[find_minor_in_three_one(cards) - 3] = -1
    if category_idx == Category.THREE_TWO.value:
        length = 1
        minor_cards[find_minor_in_three_two(cards) - 3] = -1
    if category_idx == Category.THREE_ONE_LINE.value:
        length = int(cards.size / 4)
        minor_cards[find_minor_in_three_one_line(cards) - 3] = -1
    if category_idx == Category.THREE_TWO_LINE.value:
        length = int(cards.size / 5)
        minor_cards[find_minor_in_three_two_line(cards) - 3] = -1
    if category_idx == Category.FOUR_TWO.value:
        length = 2
        minor_cards[find_minor_in_four_two(cards) - 3] = -1
    return minor_cards, length


def discounted_return(r, gamma):
    r = r.astype(float)
    r_out = np.zeros_like(r)
    val = 0
    for i in reversed(range(r.shape[0])):
        r_out[i] = r[i] + gamma * val
        val = r_out[i]
    return r_out


def get_feature_state(env, mask=None):
    curr_cards = to_char(env.get_curr_handcards())
    curr_val, curr_round = env.get_cards_value(card.Card.char2color(curr_cards))
    if mask is None:
        mask = get_mask(curr_cards, action_space, to_char(env.get_last_outcards()))
    features = np.zeros([len(mask), 9])
    features[:, 0] = mask.astype(np.int32)
    for i in range(mask.shape[0]):
        m = mask[i]
        if m:
            a = action_space[i]

            if not a:
                features[i, 1] = 1
                continue
            next_cards = curr_cards.copy()
            for c in a:
                next_cards.remove(c)
            next_val, next_round = env.get_cards_value(card.Card.char2color(next_cards))
            lose_control = env.will_lose_control(card.Card.char2value_3_17(a) + 3)
            if lose_control:
                features[i, 1] = 1
            if len(a) >= len(curr_cards):
                features[i, 2] = 1
            if next_val > curr_val:
                features[i, 3] = 1
            if next_round < curr_round:
                features[i, 4] = 1

            cnt = len(a)
            if cnt > 15:
                cnt = 15
            features[i, 5] = cnt & 8 >> 3
            features[i, 6] = cnt & 4 >> 2
            features[i, 7] = cnt & 2 >> 1
            features[i, 8] = cnt & 1
    return features


def get_masks(handcards, lastcards):
    input_single = get_mask(handcards, action_space_single, lastcards)
    input_pair = get_mask(handcards, action_space_pair, lastcards)
    input_triple = get_mask(handcards, action_space_triple, lastcards)
    input_quadric = get_mask(handcards, action_space_quadric, lastcards)
    return input_single, input_pair, input_triple, input_quadric


def normalize(cards, l, h):
    for i in range(l, h, 4):
        cnt = 0
        for j in range(i, i + 4):
            cnt += cards[j]
        for j in range(i, i + 4):
            if cnt > 0:
                cards[j] = 1
                cnt -= 1
            else:
                cards[j] = 0


def discard_onehot_from_s(s, cards_onehot):
    s[:54] -= cards_onehot
    normalize(s, 0, 52)
    s[2 * 54:3 * 54] += cards_onehot
    normalize(s, 2 * 54, 2 * 54 + 52)


# receive targets and handcards as chars
def train_fake_action(targets, handcards, s, sess, network, category_idx, main_cards_char):
    for main_card in main_cards_char:
        handcards.remove(main_card)
    cards_onehot = card.Card.char2onehot(main_cards_char)
    # we must make the order in each 4 batch correct...
    discard_onehot_from_s(s[0], cards_onehot)
    # assert np.amax(s) < 1.1 and np.amin(s) > -0.1

    is_pair = False
    if category_idx == Category.THREE_TWO.value or category_idx == Category.THREE_TWO_LINE.value:
        is_pair = True
    acc = []
    for target in targets:
        target_val = card.Card.char2value_3_17(target) - 3
        input_single, input_pair, input_triple, input_quadric = get_masks(handcards, None)

        _, response_active_output, fake_loss = sess.run([network.optimize_fake,
                                                         network.fc_response_minor_output,
                                                         network.minor_response_loss],
                                                        feed_dict={
                                                            network.input_state: s,
                                                            network.input_single: np.reshape(input_single, [1, -1]),
                                                            network.input_pair: np.reshape(input_pair, [1, -1]),
                                                            network.input_triple: np.reshape(input_triple, [1, -1]),
                                                            network.input_quadric: np.reshape(input_quadric, [1, -1]),
                                                            network.input_single_last: np.zeros([1, 15]),
                                                            network.input_pair_last: np.zeros([1, 13]),
                                                            network.input_triple_last: np.zeros([1, 13]),
                                                            network.input_quadric_last: np.zeros([1, 13]),
                                                            network.minor_response_input: np.array([target_val]),
                                                        })
        cards = [target]
        handcards.remove(target)
        if is_pair:
            if target not in handcards:
                print('something wrong...')
                print('minor', target)
                print('main_cards', main_cards_char)
                print('handcards', handcards)
            else:
                handcards.remove(target)
                cards.append(target)

        # correct for one-hot state
        cards_onehot = card.Card.char2onehot(cards)

        # print(s.shape)
        # print(cards_onehot.shape)
        discard_onehot_from_s(s[0], cards_onehot)

        acc.append(1 if np.argmax(response_active_output[0]) == target_val else 0)
    return acc


def discard_onehot_from_s_60(s, cards_onehot):
    s[:60] -= cards_onehot.astype(np.int32)
    normalize(s, 0, 60)
    # s[2 * 60:3 * 60] += cards_onehot
    # normalize(s, 2 * 60, 2 * 60 + 60)


# receive targets and handcards as chars
def train_fake_action_60(targets, handcards, s, sess, network, category_idx, main_cards_char):
    for main_card in main_cards_char:
        handcards.remove(main_card)
    cards_onehot = card.Card.char2onehot60(main_cards_char)
    # we must make the order in each 4 batch correct...
    discard_onehot_from_s_60(s, cards_onehot)

    is_pair = False
    minor_type = 0
    if category_idx == Category.THREE_TWO.value or category_idx == Category.THREE_TWO_LINE.value:
        is_pair = True
        minor_type = 1
    acc = []
    for target in targets:
        target_val = card.Card.char2value_3_17(target) - 3
        _, fc_minor_response_output = sess.run([network.optimize[-1],
                                                network.fc_minor_response_output], feed_dict={
            network.input_state: s.reshape(1, -1),
            network.minor_type: np.array([minor_type]),
            network.minor_response_input: np.array([target_val])
        })
        cards = [target]
        handcards.remove(target)
        if is_pair:
            if target not in handcards:
                print('something wrong...')
                print('minor', target)
                print('main_cards', main_cards_char)
                print('handcards', handcards)
            else:
                handcards.remove(target)
                cards.append(target)

        # correct for one-hot state
        cards_onehot = card.Card.char2onehot60(cards)

        # print(s.shape)
        # print(cards_onehot.shape)
        discard_onehot_from_s_60(s, cards_onehot)

        acc.append(1 if np.argmax(fc_minor_response_output[0]) == target_val else 0)
    return acc


def test_fake_action(targets, handcards, s, sess, network, category_idx, dup_mask, main_cards_char):
    for main_card in main_cards_char:
        handcards.remove(main_card)
    cards_onehot = card.Card.char2onehot(main_cards_char)
    discard_onehot_from_s(s[0], cards_onehot)

    is_pair = False
    if category_idx == Category.THREE_TWO.value or category_idx == Category.THREE_TWO_LINE.value:
        is_pair = True
    acc = []
    for target in targets:
        target_val = card.Card.char2value_3_17(target) - 3
        input_single, input_pair, input_triple, input_quadric = get_masks(handcards, None)
        response_minor_output = sess.run(network.fc_response_minor_output,
                                         feed_dict={
                                             network.input_state: s,
                                             network.input_single: np.reshape(input_single, [1, -1]),
                                             network.input_pair: np.reshape(input_pair, [1, -1]),
                                             network.input_triple: np.reshape(input_triple, [1, -1]),
                                             network.input_quadric: np.reshape(input_quadric, [1, -1])
                                         })
        # give minor cards
        response_minor_output = response_minor_output[0]
        response_minor_output[dup_mask == 0] = -1

        if is_pair:
            # fix dimension mismatch
            input_pair = np.concatenate([input_pair, [0, 0]])
            response_minor_output[input_pair == 0] = -1
        else:
            response_minor_output[input_single == 0] = -1

        response_minor = np.argmax(response_minor_output)
        dup_mask[response_minor] = 0

        # convert network output to char cards
        cards = [target]
        handcards.remove(target)
        if is_pair:
            handcards.remove(target)
            cards.append(target)

        # correct for one-hot state
        cards_onehot = card.Card.char2onehot(cards)

        discard_onehot_from_s(s[0], cards_onehot)

        acc.append(1 if response_minor == target_val else 0)
    return acc


def pick_minor_targets(category, cards_char):
    if category == Category.THREE_ONE.value:
        return cards_char[-1:]
    if category == Category.THREE_TWO.value:
        return cards_char[-1:]
    if category == Category.THREE_ONE_LINE.value:
        length = len(cards_char) // 4
        return cards_char[-length:]
    if category == Category.THREE_TWO_LINE.value:
        length = len(cards_char) // 5
        return cards_char[-length * 2::2]
    if category == Category.FOUR_TWO.value:
        return cards_char[-2:]
    return None


def pick_main_cards(category, cards_char):
    if category == Category.THREE_ONE.value:
        return cards_char[:-1]
    if category == Category.THREE_TWO.value:
        return cards_char[:-2]
    if category == Category.THREE_ONE_LINE.value:
        length = len(cards_char) // 4
        return cards_char[:-length]
    if category == Category.THREE_TWO_LINE.value:
        length = len(cards_char) // 5
        return cards_char[:-length * 2]
    if category == Category.FOUR_TWO.value:
        return cards_char[:-2]
    return None


def get_mask_alter(cards, last_cards, last_cards_category):
    decision_mask = None
    response_mask = None
    is_bomb = (last_cards_category == Category.QUADRIC.value)
    bomb_mask = np.zeros([13])
    length_mask = np.zeros([13, 15, 12])
    if len(last_cards) == 0:
        # category, response, length

        decision_mask = np.zeros([13])
        response_mask = np.zeros([13, 15])
        for i in range(13):
            # OFFSET ONE
            category_idx = i + 1
            subspace = action_space_category[category_idx]
            for j in range(len(subspace)):
                if counter_subset(subspace[j], cards):
                    response = card.Card.char2value_3_17(subspace[j][0]) - 3
                    response_mask[i][response] = 1
                    decision_mask[i] = 1
                    if category_idx == Category.SINGLE_LINE.value:
                        # print("single line")
                        # print("%d %d %d" % (i, response, len(subspace[j]) - 1))
                        length_mask[i][response][len(subspace[j]) - 1] = 1
                    elif category_idx == Category.DOUBLE_LINE.value:
                        length_mask[i][response][int(len(subspace[j]) / 2) - 1] = 1
                    elif category_idx == Category.TRIPLE_LINE.value:
                        length_mask[i][response][int(len(subspace[j]) / 3) - 1] = 1
                    elif category_idx == Category.THREE_ONE_LINE.value:
                        length_mask[i][response][int(len(subspace[j]) / 4) - 1] = 1
                    elif category_idx == Category.THREE_TWO_LINE.value:
                        length_mask[i][response][int(len(subspace[j]) / 5) - 1] = 1
        return decision_mask, response_mask, bomb_mask, length_mask
    else:
        decision_mask = np.ones([4])
        decision_mask[3] = 0
        if not counter_subset(['*', '$'], cards):
            decision_mask[2] = 0
        if is_bomb:
            decision_mask[1] = 0
        response_mask = np.zeros([15])
        subspace = action_space_category[last_cards_category]
        for j in range(len(subspace)):
            if counter_subset(subspace[j], cards) and card.CardGroup.to_cardgroup(subspace[j]). \
                    bigger_than(card.CardGroup.to_cardgroup(last_cards)):
                # diff = card.Card.to_value(subspace[j][0]) - card.Card.to_value(last_cards[0])
                # assert(diff > 0)
                # response_mask[diff - 1] = 1
                response_mask[card.Card.char2value_3_17(subspace[j][0]) - 3] = 1
                decision_mask[3] = 1
        if not is_bomb:
            subspace = action_space_category[Category.QUADRIC.value]
            no_bomb = True
            for j in range(len(subspace)):
                if counter_subset(subspace[j], cards):
                    bomb_mask[card.Card.char2value_3_17(subspace[j][0]) - 3] = 1
                    no_bomb = False
            # if we got no bomb, we cannot respond with bombs
            if no_bomb:
                decision_mask[1] = 0
        return decision_mask, response_mask, bomb_mask, length_mask


# return [3-17 value]
def give_cards_without_minor(response, last_cards_value, category_idx, length_output):
    # these mask will be used to tease out invalid card combinations
    # single_mask = np.zeros([15])
    # for i in range(3, 18):
    #     if i in hand_cards_value:
    #         single_mask[i - 3] = 1

    # double_mask = np.zeros([13])
    # for i in range(3, 16):
    #     if counter_subset([i, i], hand_cards_value):
    #         double_mask[i - 3] = 1

    if last_cards_value.size > 0:
        if category_idx == Category.SINGLE.value:
            return np.array([response + 3])
        elif category_idx == Category.DOUBLE.value:
            return np.array([response + 3] * 2)
        elif category_idx == Category.TRIPLE.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.QUADRIC.value:
            return np.array([response + 3] * 4)
        elif category_idx == Category.THREE_ONE.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.THREE_TWO.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.SINGLE_LINE.value:
            return np.arange(response + 3, response + 3 + len(last_cards_value))
        elif category_idx == Category.DOUBLE_LINE.value:
            link = np.arange(response + 3,
                             response + 3 + int(len(last_cards_value) / 2))
            return np.array([link, link]).T.reshape(-1)
        elif category_idx == Category.TRIPLE_LINE.value:
            link = np.arange(response + 3,
                             response + 3 + int(len(last_cards_value) / 3))
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.THREE_ONE_LINE.value:
            cnt = int(len(last_cards_value) / 4)
            link = np.arange(response + 3, response + 3 + cnt)
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.THREE_TWO_LINE.value:
            cnt = int(len(last_cards_value) / 5)
            link = np.arange(response + 3, response + 3 + cnt)
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.FOUR_TWO.value:
            return np.array([response + 3] * 4)
    else:
        if category_idx == Category.SINGLE.value:
            return np.array([response + 3])
        elif category_idx == Category.DOUBLE.value:
            return np.array([response + 3] * 2)
        elif category_idx == Category.TRIPLE.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.QUADRIC.value:
            return np.array([response + 3] * 4)
        elif category_idx == Category.THREE_ONE.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.THREE_TWO.value:
            return np.array([response + 3] * 3)
        elif category_idx == Category.SINGLE_LINE.value:
            # length output will be in range 1-12
            return np.arange(response + 3, response + 3 + length_output)
        elif category_idx == Category.DOUBLE_LINE.value:
            link = np.arange(response + 3, response + 3 + length_output)
            return np.array([link, link]).T.reshape(-1)
        elif category_idx == Category.TRIPLE_LINE.value:
            link = np.arange(response + 3, response + 3 + length_output)
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.THREE_ONE_LINE.value:
            cnt = length_output
            link = np.arange(response + 3, response + 3 + cnt)
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.THREE_TWO_LINE.value:
            cnt = length_output
            link = np.arange(response + 3, response + 3 + cnt)
            return np.array([link, link, link]).T.reshape(-1)
        elif category_idx == Category.FOUR_TWO.value:
            return np.array([response + 3] * 4)
        elif category_idx == Category.BIGBANG.value:
            return np.array([16, 17])


# assumes that cards has been grouped with minor cards in the end
def get_category_idx(cards):
    size = cards.size
    setsize = len(set(cards))
    if size == 0:
        return Category.EMPTY.value
    if size == 1:
        return Category.SINGLE.value
    if size == 2:
        if cards[0] == cards[1]:
            return Category.DOUBLE.value
        return Category.BIGBANG.value
    if size == 3:
        return Category.TRIPLE.value
    if size == 4:
        if setsize == 1:
            return Category.QUADRIC.value
        return Category.THREE_ONE.value
    if size == 5 and setsize == 2:
        return Category.THREE_TWO.value
    if size == 6 and cards[3] == cards[0]:
        return Category.FOUR_TWO.value
    if cards[0] != cards[1]:
        return Category.SINGLE_LINE.value
    if cards[0] != cards[2]:
        return Category.DOUBLE_LINE.value
    if setsize * 3 == size:
        return Category.TRIPLE_LINE.value
    if setsize * 2 == size:
        return Category.THREE_ONE_LINE.value
    return Category.THREE_TWO_LINE.value


def discard_cards(handcards, intention):
    for card in intention:
        for i in range(handcards.size):
            if handcards[i] == card:
                handcards = np.delete(handcards, i)
                break


# return char minor cards output
def inference_minor_util(s, handcards, sess, network, num, is_pair, dup_mask, main_cards_char):
    for main_card in main_cards_char:
        handcards.remove(main_card)
    cards_onehot = card.Card.char2onehot(main_cards_char)
    discard_onehot_from_s(s[0], cards_onehot)

    outputs = []
    inter_states = []
    inter_masks = []
    inter_outputs = []
    for i in range(num):
        # update mask for the next loop
        input_single, input_pair, input_triple, input_quadric = get_masks(handcards, None)

        inter_states.append(s.copy())
        inter_masks.append([input_single, input_pair, input_triple, input_quadric])

        response_minor_output = scheduled_run(sess, network.fc_minor_response_output,
                                              (
                                                  (network.input_state, s),
                                                  (network.input_single, np.reshape(input_single, [1, -1])),
                                                  (network.input_pair, np.reshape(input_pair, [1, -1])),
                                                  (network.input_triple, np.reshape(input_triple, [1, -1])),
                                                  (network.input_quadric, np.reshape(input_quadric, [1, -1]))
                                              ))
        # response_active_output = sess.run(network.fc_response_active_output,
        #                                   feed_dict={
        #                                       network.input_state: s,
        #                                       network.input_single: np.reshape(input_single, [1, -1]),
        #                                       network.input_pair: np.reshape(input_pair, [1, -1]),
        #                                       network.input_triple: np.reshape(input_triple, [1, -1]),
        #                                       network.input_quadric: np.reshape(input_quadric, [1, -1])
        #                                   })

        # give minor cards
        response_minor_output = response_minor_output[0]
        response_minor_output[dup_mask == 0] = -1
        # print(handcards)
        if is_pair:
            input_pair = np.concatenate([input_pair, [0, 0]])
            response_minor_output[input_pair == 0] = -1
        else:
            response_minor_output[input_single == 0] = -1

        response_minor = np.argmax(response_minor_output)
        inter_outputs.append(response_minor)
        dup_mask[response_minor] = 0

        # convert network output to char cards
        cards = [to_char(response_minor + 3)]
        handcards.remove(to_char(response_minor + 3))
        if is_pair:
            handcards.remove(to_char(response_minor + 3))
            cards.append(to_char(response_minor + 3))

        # correct for one-hot state
        cards_onehot = card.Card.char2onehot(cards)

        discard_onehot_from_s(s[0], cards_onehot)

        # save to output
        outputs.append(to_char(response_minor + 3))
        if is_pair:
            outputs.append(to_char(response_minor + 3))
    return outputs, inter_states, inter_masks, inter_outputs


def inference_minor_cards(category, s, handcards, sess, network, seq_length, dup_mask, main_cards_char):
    if category == Category.THREE_ONE.value:
        return inference_minor_util(s, handcards, sess, network, 1, False, dup_mask, main_cards_char)
    if category == Category.THREE_TWO.value:
        return inference_minor_util(s, handcards, sess, network, 1, True, dup_mask, main_cards_char)
    if category == Category.THREE_ONE_LINE.value:
        return inference_minor_util(s, handcards, sess, network, seq_length, False, dup_mask, main_cards_char)
    if category == Category.THREE_TWO_LINE.value:
        return inference_minor_util(s, handcards, sess, network, seq_length, True, dup_mask, main_cards_char)
    if category == Category.FOUR_TWO.value:
        return inference_minor_util(s, handcards, sess, network, 2, False, dup_mask, main_cards_char)


# return char minor cards output
def inference_minor_util60(s, handcards, sess, network, num, is_pair, dup_mask, main_cards_char):
    for main_card in main_cards_char:
        handcards.remove(main_card)
    cards_onehot = card.Card.char2onehot60(main_cards_char)
    discard_onehot_from_s_60(s[0], cards_onehot)

    outputs = []
    inter_states = []
    inter_outputs = []
    minor_type = 1 if is_pair else 0
    for i in range(num):
        inter_states.append(s.copy())
        input_single, input_pair, _, _ = get_masks(handcards, None)
        response_minor_output = scheduled_run(sess, network.fc_minor_response_output,
                                              (
                                                  (network.input_state, s),
                                                  (network.minor_type, np.array([minor_type]))
                                              ))

        # give minor cards
        response_minor_output = response_minor_output[0]
        response_minor_output[dup_mask == 0] = -1
        # print(handcards)
        if is_pair:
            input_pair = np.concatenate([input_pair, [0, 0]])
            response_minor_output[input_pair == 0] = -1
        else:
            response_minor_output[input_single == 0] = -1

        response_minor = np.argmax(response_minor_output)
        inter_outputs.append(response_minor)
        dup_mask[response_minor] = 0

        # convert network output to char cards
        cards = [to_char(response_minor + 3)]
        handcards.remove(to_char(response_minor + 3))
        if is_pair:
            handcards.remove(to_char(response_minor + 3))
            cards.append(to_char(response_minor + 3))

        # correct for one-hot state
        cards_onehot = card.Card.char2onehot60(cards)

        discard_onehot_from_s_60(s[0], cards_onehot)

        # save to output
        outputs.append(to_char(response_minor + 3))
        if is_pair:
            outputs.append(to_char(response_minor + 3))
    return outputs, inter_states, inter_outputs


def inference_minor_cards60(category, s, handcards, sess, network, seq_length, dup_mask, main_cards_char):
    if category == Category.THREE_ONE.value:
        return inference_minor_util60(s, handcards, sess, network, 1, False, dup_mask, main_cards_char)
    if category == Category.THREE_TWO.value:
        return inference_minor_util60(s, handcards, sess, network, 1, True, dup_mask, main_cards_char)
    if category == Category.THREE_ONE_LINE.value:
        return inference_minor_util60(s, handcards, sess, network, seq_length, False, dup_mask, main_cards_char)
    if category == Category.THREE_TWO_LINE.value:
        return inference_minor_util60(s, handcards, sess, network, seq_length, True, dup_mask, main_cards_char)
    if category == Category.FOUR_TWO.value:
        return inference_minor_util60(s, handcards, sess, network, 2, False, dup_mask, main_cards_char)


class GPUTime:
    total_time = 0


@contextmanager
def timeblock(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print('time {} : {}'.format(label, end - start))


@contextmanager
def gputimeblock(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        GPUTime.total_time += end - start


def update_params(scope_from, scope_to):
    vars_from = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope_from)
    vars_to = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope_to)

    ops = []
    for from_var, to_var in zip(vars_from, vars_to):
        if 'value_output' not in from_var.name:
            ops.append(to_var.assign(from_var))
    return ops


if __name__ == '__main__':
    # _, response_mask, _, _ = get_mask_alter(['A', 'A', 'A', 'J', 'J', '10', '6', '6', '5'], ['9', '9', '9', '5'],
    # False, 5)
    pass
    # for i in range(14):
    #     for j in range(len(action_space_category[i])):
    #         try:
    #             assert get_category_idx(np.array(action_space_category[i][j])) == i
    #         except AssertionError as error:
    #             print(i, action_space_category[i][j])
