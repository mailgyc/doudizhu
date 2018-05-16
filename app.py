import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.options import define, options

from db import torndb
from settings import settings, DATABASE, LOGGING
from urls import url_patterns

logging.config.dictConfig(LOGGING)


class Application(tornado.web.Application):
    def __init__(self):
        super().__init__(url_patterns, **settings)
        self.db = torndb.Connection(**DATABASE)
        self.executor = ThreadPoolExecutor()


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    logging.info(f'listening on {options.port}')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
