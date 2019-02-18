import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.websocket
from tornado.ioloop import IOLoop
from tornado.options import options

from apps.urls import url_patterns
from contrib.db import AsyncConnection
from settings import settings

logging.config.dictConfig(settings.LOGGING)

# APPLICATION = {
#     'login_url': '/',
#     'xheaders': True,
# }


class Application(tornado.web.Application):
    settings = {
        'debug': settings.DEBUG,
        'gzip': getattr(settings, 'GZIP', False),
        'cookie_secret': settings.SECRET_KEY,
        'xsrf_cookies': getattr(settings, 'XSRF_COOKIES', True),
        'autoescape': "xhtml_escape",
        'template_path': settings.TEMPLATE_ROOT,
        'static_path': settings.STATIC_ROOT,
        'static_url_prefix': settings.STATIC_URL,
    }

    def __init__(self):
        super().__init__(url_patterns, **self.settings)
        self.db = AsyncConnection(**settings.DATABASE)
        self.executor = ThreadPoolExecutor()


def make_app(port):
    app = Application()
    app.listen(port)
    return app


def main():
    make_app(settings.PORT)
    logging.info(f'server on http://127.0.0.1:{settings.PORT}')
    IOLoop.current().start()


if __name__ == '__main__':
    main()
