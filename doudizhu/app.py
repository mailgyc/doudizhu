import asyncio
import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.locks
import tornado.web
import tornado.websocket

from apps.urls import url_patterns
from settings import DEBUG, LOGGING, PORT, SECRET_KEY, TEMPLATE_ROOT, STATIC_ROOT, STATIC_URL

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
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.allow_robot = True


async def main():
    app = Application()
    app.listen(PORT)
    logging.info(f'server on http://127.0.0.1:{PORT}')
    shutdown_event = tornado.locks.Event()
    await shutdown_event.wait()


if __name__ == '__main__':
    asyncio.run(main())
