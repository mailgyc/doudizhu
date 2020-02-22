from __future__ import annotations

import logging
import random
from typing import Optional, List
from typing import TYPE_CHECKING

from tornado.ioloop import IOLoop

from .protocol import Protocol as Pt
from .rule import rule

if TYPE_CHECKING:
    from .player import Player


class Room(object):

    def __init__(self, room_id, level=1, allow_robot=True):
        self.room_id = room_id
        self.base = level * 10
        self.multiple = 0

        self.players: List[Optional[Player]] = [None, None, None]
        self.pokers: List[int] = []

        self.timer = 30
        self.whose_turn = 0
        self.landlord_seat = 0
        self.bomb_multiple = 2

        self.last_shot_seat = 0
        self.last_shot_poker: List[int] = []
        self.shot_round: List[List[int]] = []

        self.allow_robot = allow_robot

    def restart(self):
        self.multiple = 15
        self.pokers: List[int] = []

        self.timer = 30
        self.whose_turn = 0
        self.landlord_seat = (self.landlord_seat + 1) % 3
        self.bomb_multiple = 2

        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.shot_round = []

        for player in self.players:
            if player.leave == 0:
                player.restart()
            else:
                IOLoop.current().add_callback(player.leave_room)

    def sync_data(self):
        return {
            'id': self.room_id,
            'base': self.base,
            'multiple': self.multiple,
            'state': self.players[0].state,
            'landlord_uid': self.seat_to_uid(self.landlord_seat),
            'whose_turn': self.seat_to_uid(self.whose_turn),
            'timer': self.timer,
            'last_shot_uid': self.seat_to_uid(self.last_shot_seat),
            'last_shot_poker': self.last_shot_poker,
        }

    def broadcast(self, response):
        for player in self.players:
            if player and player.leave == 0:
                player.write_message(response)

    def sync_room(self):
        for player in self.players:
            if player and player.leave == 0:
                response = [Pt.RSP_JOIN_ROOM, {
                    'room': self.sync_data(),
                    'players': [p.sync_data(p == player) if p else {} for p in self.players]
                }]
                player.write_message(response)

    def add_robot(self, nth=1):
        size = self.size()
        if size == 0 or size == 3:
            return

        if size == 2 and nth == 1:
            # only allow [human robot robot]
            return

        from .components.simple import RobotPlayer
        p1 = RobotPlayer(10 + nth, f'IDIOT-{nth}', self)
        p1.to_server([Pt.REQ_JOIN_ROOM, {'room': self.room_id, 'level': 1}])

        if nth == 1:
            IOLoop.current().call_later(1, self.add_robot, nth=2)

    def _on_join(self, target: Player):
        for i, player in enumerate(self.players):
            if player:
                continue
            target.seat = i
            self.players[i] = target
            return True
        return False

    def on_join(self, target: Player):
        if self._on_join(target):
            if self.allow_robot:
                IOLoop.current().call_later(0.1, self.add_robot, nth=1)
            return True
        return False

    def on_shot(self, seat: int, pokers: List[int]) -> str:
        if pokers:
            spec = rule.get_poker_spec(pokers)
            if spec is None:
                return 'Poker does not comply with the rules'

            if seat != self.last_shot_seat and rule.compare_pokers(pokers, self.last_shot_poker) < 0:
                return 'Poker small than last shot'

            if spec == 'bomb' or spec == 'rocket':
                self.multiple *= self.bomb_multiple

            self.last_shot_seat = seat
            self.last_shot_poker = pokers
        else:
            if seat == self.last_shot_seat:
                return 'Last shot player does not allow pass'

        self.shot_round.append(pokers)
        return ''

    def on_leave(self, target: Player):
        from .components.simple import RobotPlayer
        from .storage import Storage
        try:
            for i, player in enumerate(self.players):
                if player == target:
                    self.players[i] = None
                elif isinstance(player, RobotPlayer):
                    self.players[i] = None

            Storage.on_room_changed(self)
            return True
        except ValueError:
            logging.error('Player[%d] NOT IN Room[%d]', target.uid, self.room_id)
            return False

    def on_game_over(self, winner: Player):

        spring = self.is_spring(winner)
        anti_spring = self.anti_spring(winner)
        if spring or anti_spring:
            self.multiple *= 3

        point = self.base * self.multiple
        response = [Pt.RSP_GAME_OVER, {
            'winner': winner.uid,
            'spring': int(self.is_spring(winner)),
            'antispring': int(self.anti_spring(winner)),
            'multiple': self.multiple,
            'players': [],
        }]
        for player in self.players:
            response[1]['players'].append({
                'uid': player.uid,
                'point': point,
                'pokers': player.hand_pokers,
            })
        self.broadcast(response)
        logging.info('Room[%d] GameOver', self.room_id)

        IOLoop.current().add_callback(self.restart)

    def is_spring(self, winner: Player) -> bool:
        if self.landlord == winner:
            for i, poker in enumerate(self.shot_round):
                if i % 3 == 0:
                    continue
                if poker:
                    return False
            return True
        return False

    def anti_spring(self, winner: Player) -> bool:
        if self.landlord == winner:
            return False

        for i, poker in enumerate(self.shot_round):
            if i == 0:
                continue
            if i % 3 == 0 and poker:
                return False
        return True

    def deal_poker(self):
        try:
            from .dealer import generate_pokers
            self.pokers = generate_pokers(self.allow_robot)
        except ModuleNotFoundError:
            self.pokers = list(range(1, 55))
            random.shuffle(self.pokers)
            logging.info('RANDOM POKERS')

        for i in range(3):
            self.players[i].push_pokers(self.pokers[i * 17: (i + 1) * 17])

        self.pokers = self.pokers[51:]

        self.whose_turn = self.landlord_seat
        for player in self.players:
            response = [Pt.RSP_DEAL_POKER, {
                'uid': self.turn_player.uid,
                'timer': self.timer,
                'pokers': player.hand_pokers
            }]
            if player.leave == 0:
                player.write_message(response)
            logging.info('ROOM[%s] DEAL[%s]', self.room_id, response)

    def go_next_turn(self):
        self.whose_turn += 1
        if self.whose_turn == 3:
            self.whose_turn = 0

    def go_prev_turn(self):
        self.whose_turn -= 1
        if self.whose_turn == -1:
            self.whose_turn = 2

    def seat_to_uid(self, seat):
        if self.players[seat]:
            return self.players[seat].uid
        return -1

    @property
    def landlord(self):
        for player in self.players:
            if player.landlord == 1:
                return player
        return None

    @property
    def prev_player(self):
        prev_seat = (self.whose_turn - 1) % 3
        return self.players[prev_seat]

    @property
    def turn_player(self):
        return self.players[self.whose_turn]

    @property
    def next_player(self):
        next_seat = (self.whose_turn + 1) % 3
        return self.players[next_seat]

    def is_rob_end(self) -> bool:
        if not self._is_rob_end():
            self.go_next_turn()
            return False

        for i in range(3):
            # 每个人都抢地主, 第一个人是地主
            if self.turn_player.rob == 1 or i == 2:
                self.turn_player.landlord = 1
                self.turn_player.push_pokers(self.pokers)
                self.last_shot_seat = self.whose_turn
                self.re_multiple()
                return True
            self.go_prev_turn()
        return True

    def re_multiple(self):
        joker_number = rule.count_joker(self.pokers)
        if joker_number > 0:
            self.multiple = self.multiple * 2 * joker_number
            return

        if rule.is_same_color(self.pokers):
            self.multiple *= 2
            self.bomb_multiple = 4

    def _is_rob_end(self) -> bool:
        """
        每人都可以抢一次地主, 第一个人可以多抢一次
        :return: 抢地主是否结束
        """
        # 下一个人没有抢地主, 继续抢地主
        if self.next_player.rob == -1:
            return False

        # 抢了一圈, 处理第一个人多抢一次
        if self.next_player.seat == self.landlord_seat:
            # 第一个人第一次没有抢, 结束
            if self.next_player.rob == 0:
                return True

            if self.turn_player.rob == 0:
                # 当前用户没有抢
                if self.prev_player.rob == 0:
                    # 前一个用户也没有抢, 第一个人是地主, 结束
                    return True
                else:
                    # 前一个用户抢了, 第一个人可以多抢一次, 继续抢
                    return False
            else:
                # 当前用户抢了, 第一个人可以多抢一次, 继续抢
                return False

        # 第一个人也抢了, 结束
        return True

    def is_ready(self) -> bool:
        return self.is_full() and all([p.ready for p in self.players])

    def is_full(self) -> bool:
        return self.size() == 3

    def is_empty(self) -> bool:
        return self.size() == 0

    def has_robot(self) -> bool:
        from .components.simple import RobotPlayer
        return any([isinstance(p, RobotPlayer) for p in self.players])

    def size(self):
        return sum([p is not None for p in self.players])

    def __str__(self):
        return f'[{self.room_id}{[p or "-" for p in self.players]}]'

    def __hash__(self):
        return self.room_id

    def __eq__(self, other):
        return self.room_id == other.room_id

    def __ne__(self, other):
        return not (self == other)