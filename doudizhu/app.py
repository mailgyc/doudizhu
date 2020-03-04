import asyncio
import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.websocket

from apps.urls import url_patterns
from contrib.db import AsyncConnection
from settings import DEBUG, DATABASE, LOGGING, PORT, SECRET_KEY, TEMPLATE_ROOT, STATIC_ROOT, STATIC_URL

logging.config.dictConfig(LOGGING)


# try:
#     import uvloop
#     uvloop.install()
# except ModuleNotFoundError:
#     pass


class Application(tornado.web.Application):
    settings = {
        'debug': DEBUG,
        'cookie_secret': SECRET_KEY,
        'xsrf_cookies': False,
        'gzip': True,
        'autoescape': 'xhtml_escape',
        'template_path': TEMPLATE_ROOT,
        'static_path': STATIC_ROOT,
        'static_url_prefix': STATIC_URL,
        'login_url': '/login',
    }

    def __init__(self):
        super().__init__(url_patterns, **self.settings)
        self.db = AsyncConnection(**DATABASE)
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.allow_robot = True


def make_app(port):
    app = Application()
    app.listen(port)
    return app


def main():
    make_app(PORT)
    logging.info(f'server on http://127.0.0.1:{PORT}')
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
