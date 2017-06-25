import random

from core.player import Player
from net.protocol import Protocol as Pt


class AiPlayer(Player):

    def __init__(self, uid: int, username: str):
        from net.loopback import LoopBackSocketHandler
        super().__init__(uid, username, LoopBackSocketHandler(self))

    def start_call_score(self, min_score):
        millis = random.randint(1000, 2000)
        score = random.randint(min_score + 1, 3)
        self.handle_call_score(score)

    def play_poker(self, last_turn_poker):
        pokers = []  # this.hint(last_turn_poker);
        millis = random.randint(500, 1000)
        self.shot_poker(pokers)

    def send(self, packet):
        self.socket.write_message(packet)
        if packet[0] == Pt.RSP_DEAL_POKER:
            caller = packet[1]
            if caller == self.uid:
                self.send([Pt.REQ_CALL_SCORE, 2])
