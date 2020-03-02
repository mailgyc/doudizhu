import time
from typing import Callable

from tornado.ioloop import IOLoop


class Timer(object):

    def __init__(self, callback: Callable, timeout: int = 20):
        self._callback = callback
        self._timeout = timeout
        self._is_running = False
        self._last_time = time.time()

    @property
    def timeout(self) -> int:
        return max(self._timeout - int(time.time() - self._last_time), 0)

    def start_timing(self, timeout: int = 20):
        if timeout:
            self._timeout = timeout

        self._last_time = time.time()
        if not self._is_running:
            IOLoop.current().call_later(1, self._on_time)
        self._is_running = True

    def stop_timing(self):
        self._is_running = False

    def _on_time(self):
        if self._is_running:
            return
        if time.time() - self._last_time >= self._timeout:
            self._callback()
        else:
            IOLoop.current().call_later(1, self._on_time)
