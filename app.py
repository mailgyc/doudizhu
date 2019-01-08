import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.websocket
from tornado.ioloop import IOLoop
from tornado.options import options

from db import aio_db
from settings.base import APPLICATION, DATABASE, LOGGING
from settings.urls import url_patterns

logging.config.dictConfig(LOGGING)


class WebApp(tornado.web.Application):
    def __init__(self):
        super().__init__(url_patterns, **APPLICATION)
        self.db = aio_db.AsyncConnection(**DATABASE)
        self.executor = ThreadPoolExecutor()


def main():
    app = WebApp()
    app.listen(options.port)
    logging.info(f'server on http://127.0.0.1:{options.port}')
    IOLoop.current().start()


if __name__ == '__main__':
    main()
