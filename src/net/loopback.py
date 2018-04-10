from tornado.ioloop import IOLoop

from net.socket import SocketHandler


class LoopBackSocketHandler(SocketHandler):

    def __init__(self, player):
        self.player = player

    def write_message(self, message, binary=True):
        IOLoop.current().add_callback(self._write_message, message)
        return True

    def _write_message(self, packet):
        self.player.from_server(packet)
