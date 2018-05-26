import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.websocket
from tornado.ioloop import IOLoop
from tornado.options import options

from db import torndb
from settings.base import settings, DATABASE, LOGGING
from urls import url_patterns

logging.config.dictConfig(LOGGING)


class WebApp(tornado.web.Application):
    def __init__(self):
        super().__init__(url_patterns, **settings)
        self.db = torndb.Connection(**DATABASE)
        self.executor = ThreadPoolExecutor()


def main():
    app = WebApp()
    app.listen(options.port)
    logging.info(f'listening on {options.port}')
    IOLoop.current().start()


if __name__ == '__main__':
    main()
