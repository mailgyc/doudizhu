from apps.account.views import IndexHandler, LoginHandler, UserInfoHandler
from apps.game.views import SocketHandler

url_patterns = [
    ('/', IndexHandler),
    ('/login', LoginHandler),
    ('/userinfo', UserInfoHandler),
    ('/ws', SocketHandler),
]
