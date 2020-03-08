from __future__ import annotations

import logging
import random
from functools import reduce
from operator import mul
from typing import Optional, List, Dict
from typing import TYPE_CHECKING

from tornado.ioloop import IOLoop

from .protocol import Protocol as Pt
from .rule import rule
from .timer import Timer

if TYPE_CHECKING:
    from .player import Player


class Room(object):
    robot_no = 0

    def __init__(self, room_id, level=1, allow_robot=True):
        self.room_id = room_id
        self.level = level
        self._multiple_details: Dict[str, int] = {
            'origin': 10,
            'origin_multiple': 15,
            'di': 1,
            'ming': 1,
            'bomb': 1,
            'rob': 1,
            'spring': 1,
            'landlord': 1,
            'farmer': 1,
        }

        self.players: List[Optional[Player]] = [None, None, None]
        self.pokers: List[int] = []

        self.timer = Timer(self.on_timeout)
        self.whose_turn = 0
        self.landlord_seat = 0
        self.bomb_multiple = 2

        self.last_shot_seat = 0
        self.last_shot_poker: List[int] = []
        self.shot_round: List[List[int]] = []

        self.allow_robot = allow_robot

    def restart(self):
        for key, val in self._multiple_details.items():
            if key.startswith('origin'):
                continue
            self._multiple_details[key] = 1

        self.pokers: List[int] = []

        self.timer.stop_timing()
        self.whose_turn = 0
        self.landlord_seat = (self.landlord_seat + 1) % 3
        self.bomb_multiple = 2

        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.shot_round = []

        for player in self.players:
            if player.is_left():
                IOLoop.current().add_callback(self.on_leave, player, True)
            else:
                player.restart()

    @property
    def room_state(self):
        from .player import State
        for player in self.players:
            if player and not player.is_left():
                return player.state
        return State.INIT

    def sync_data(self):
        return {
            'id': self.room_id,
            'origin': self._multiple_details['origin'],
            'multiple': self.multiple,
            'state': self.room_state,
            'landlord_uid': self.seat_to_uid(self.landlord_seat),
            'whose_turn': self.seat_to_uid(self.whose_turn),
            'timer': self.timer.timeout,
            'last_shot_uid': self.seat_to_uid(self.last_shot_seat),
            'last_shot_poker': self.last_shot_poker,
        }

    def broadcast(self, response):
        for player in self.players:
            if player and not player.is_left():
                player.write_message(response)

    def sync_room(self):
        for player in self.players:
            if player and not player.is_left():
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

        if nth == 1 and self.robot_no > 5:
            # limit robot number
            return

        from .components.simple import RobotPlayer
        p1 = RobotPlayer(10000 + nth, f'IDIOT-{nth}', self)
        p1.to_server(Pt.REQ_JOIN_ROOM, {'room': self.room_id, 'level': 1})

        if nth == 1:
            IOLoop.current().call_later(3, self.add_robot, nth=2)
            self.robot_no += 1

    def on_timeout(self):
        self.turn_player.on_timeout()

    def on_join(self, target: Player):
        if self._on_join(target):
            if self.allow_robot and self.level == 1:
                IOLoop.current().call_later(10, self.add_robot, nth=1)
            return True
        return False

    def on_rob(self, target: Player) -> bool:
        if target.rob == 1:
            self._multiple_details['rob'] *= 2

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

    def on_deal_poker(self):
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
        self.timer.start_timing(self.turn_player.timeout)
        for player in self.players:
            response = [Pt.RSP_DEAL_POKER, {
                'uid': self.turn_player.uid,
                'timer': self.timer.timeout,
                'pokers': player.hand_pokers
            }]
            if not player.is_left():
                player.write_message(response)
            logging.info('ROOM[%s] DEAL[%s]', self.room_id, response)

    def on_shot(self, seat: int, pokers: List[int]) -> str:
        if pokers:
            spec = rule.get_poker_spec(pokers)
            if spec is None:
                return 'Poker does not comply with the rules'

            if seat != self.last_shot_seat and rule.compare_pokers(pokers, self.last_shot_poker) < 0:
                return 'Poker small than last shot'

            if spec == 'bomb' or spec == 'rocket':
                self._multiple_details['bomb'] *= 2

            self.last_shot_seat = seat
            self.last_shot_poker = pokers
        else:
            if seat == self.last_shot_seat:
                return 'Last shot player does not allow pass'

        self.shot_round.append(pokers)
        return ''

    def on_leave(self, target: Player, is_restart=False):
        from .components.simple import RobotPlayer
        from .storage import Storage
        try:
            free_robot = 0
            for i, player in enumerate(self.players):
                if player == target:
                    self.players[i] = None
                elif is_restart and isinstance(player, RobotPlayer):
                    self.players[i] = None
                    free_robot = 1

            self.robot_no -= free_robot
            Storage.on_room_changed(self)
            return True
        except ValueError:
            logging.error('Player[%d] NOT IN Room[%d]', target.uid, self.room_id)
            return False

    def on_game_over(self, winner: Player):
        spring = self.is_spring(winner)
        anti_spring = self.anti_spring(winner)
        if spring or anti_spring:
            self._multiple_details['spring'] *= 3

        response = [Pt.RSP_GAME_OVER, {
            'winner': winner.uid,
            'spring': int(self.is_spring(winner)),
            'antispring': int(self.anti_spring(winner)),
            'multiple': self._multiple_details,
            'players': [],
        }]
        for player in self.players:
            point = self.get_point(winner, player)
            response[1]['players'].append({
                'uid': player.uid,
                'point': point,
                'pokers': player.hand_pokers,
            })
        self.broadcast(response)
        logging.info('Room[%d] GameOver', self.room_id)

        self.timer.stop_timing()
        IOLoop.current().add_callback(self.restart)

    @property
    def multiple(self) -> int:
        return reduce(mul, self._multiple_details.values(), 1) // self._multiple_details['origin']

    def re_multiple(self):
        joker_number = rule.get_joker_no(self.pokers)
        if joker_number > 0:
            self._multiple_details['di'] *= 2 * joker_number
            return

        if rule.is_same_color(self.pokers):
            self._multiple_details['di'] *= 2

        if rule.is_short_seq(self.pokers):
            self._multiple_details['di'] *= 2

    def get_point(self, winner: Player, player: Player) -> int:
        point = reduce(mul, self._multiple_details.values(), 1)
        if self.landlord == winner:
            if winner == player:
                return point * 2
            else:
                return -point
        else:
            if player.landlord == 0:
                return point
            else:
                return -point * 2

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

    def _on_join(self, target: Player):
        for i, player in enumerate(self.players):
            if player:
                continue
            target.seat = i
            self.players[i] = target
            return True
        return False

    def go_next_turn(self):
        self.whose_turn += 1
        if self.whose_turn == 3:
            self.whose_turn = 0
        self.timer.start_timing(self.turn_player.timeout)

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
