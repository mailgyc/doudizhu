import json
import logging

from tornado.ioloop import IOLoop

from core import rule
from core.player import Player
from core.predictor import Predictor
from tensorpack import *
from core.DQNModel import Model
from handlers.protocol import Protocol as Pt
import numpy as np
from core.extra.card import Card

logger = logging.getLogger('ddz')


class AiPlayer(Player):

    def __init__(self, uid: int, username: str, player: Player):
        from handlers.loopback import LoopBackSocketHandler
        super().__init__(uid, username, LoopBackSocketHandler(self))
        self.room = player.room
        self.predictor = Predictor(OfflinePredictor(PredictConfig(
            model=Model(),
            session_init=SaverRestore('C:/Users/44762/PycharmProjects/doudizhu-tornado/core/res/model-92500'),
            input_names=['state', 'comb_mask', 'fine_mask'],
            output_names=['Qvalue']
        )))

    def to_server(self, message):
        packet = json.dumps(message)
        IOLoop.current().add_callback(self.socket.on_message, packet)
        logger.info('AI[%d] REQ: %s', self.uid, message)

    def from_server(self, packet):
        logger.info('AI[%d] ON: %s', self.uid, packet)
        code = packet[0]
        if code == Pt.RSP_LOGIN:
            pass
        elif code == Pt.RSP_TABLE_LIST:
            pass
        elif code == Pt.RSP_JOIN_TABLE:
            pass
        elif code == Pt.RSP_DEAL_POKER:
            if self.uid == packet[1]:
                self.auto_call_score()
        elif code == Pt.RSP_CALL_SCORE:
            if self.table.turn_player == self:
                # caller = packet[1]
                # score = packet[2]
                call_end = packet[3]
                if not call_end:
                    self.auto_call_score()
                else:
                    self.auto_shot_poker()
        elif code == Pt.RSP_SHOW_POKER:
            if self.table.turn_player == self:
                self.auto_shot_poker()
        elif code == Pt.RSP_SHOT_POKER:
            if self.table.turn_player == self:
                self.auto_shot_poker()
        elif code == Pt.RSP_GAME_OVER:
            winner = packet[1]
            coin = packet[2]
        else:
            logger.info('AI ERROR PACKET: %s', packet)

    def auto_call_score(self, score=0):
        # millis = random.randint(1000, 2000)
        # score = random.randint(min_score + 1, 3)
        packet = [Pt.REQ_CALL_SCORE, self.table.call_score + 1]
        IOLoop.current().add_callback(self.to_server, packet)

    def auto_shot_poker(self):
        pokers = []

        def to_char(pokers):
            cards = rule._to_cards(pokers)
            for i, card in enumerate(cards):
                if card == 'w':
                    cards[i] = '*'
                elif card == 'W':
                    cards[i] = '$'
                elif card == '0':
                    cards[i] = '10'
            return cards
        handcards_char = to_char(self.hand_pokers)
        last_cards_char = to_char(self.table.last_shot_poker)
        print(handcards_char)
        print(last_cards_char)
        if self.table.last_shot_seat == self.seat:
            last_cards_char = []

        total_cards = np.ones([60])
        total_cards[53:56] = 0
        total_cards[57:60] = 0
        remain_cards = total_cards - Card.char2onehot60(handcards_char +
                                                        to_char(self.table.history[self.seat] +
                                                                self.table.history[(self.seat + 1) % 3] +
                                                                self.table.history[(self.seat + 2) % 3]))
        next_cnt = len(self.table.players[(self.seat + 1) % 3].hand_pokers)
        next_next_cnt = len(self.table.players[(self.seat + 2) % 3].hand_pokers)
        next_state = remain_cards * (next_cnt / (next_cnt + next_next_cnt))
        next_next_state = remain_cards * (next_next_cnt / (next_cnt + next_next_cnt))
        prob_state = np.concatenate([next_state, next_next_state])
        assert np.all(prob_state < 1.) and np.all(prob_state >= 0.)
        # print(self.table.last_shot_poker)
        # print(self.hand_pokers)
        # print(self.table.players[self.seat].hand_pokers)
        intention = self.predictor.predict(handcards_char, last_cards_char, prob_state)
        print(intention)

        def to_pokers(cards):
            for i, card in enumerate(cards):
                if card == '*':
                    cards[i] = 'w'
                elif card == '$':
                    cards[i] = 'W'
                elif card == '10':
                    cards[i] = '0'
            return rule._to_pokers(self.hand_pokers, cards)
        # if not self.table.last_shot_poker or self.table.last_shot_seat == self.seat:
        #     pokers.append(self.hand_pokers[0])
        # else:
        #     pokers = rule.cards_above(self.hand_pokers, self.table.last_shot_poker)
        pokers = to_pokers(intention)
        packet = [Pt.REQ_SHOT_POKER, pokers]
        # IOLoop.current().add_callback(self.to_server, packet)
        IOLoop.current().call_later(2, self.to_server, packet)

