import msgpack

from net.socket import SocketHandler


class LoopBackSocketHandler(SocketHandler):

    def __init__(self, player):
        self.player = player

    def write_message(self, message, binary=True):
        packet = msgpack.packb(message)
        return self.on_message(packet)
