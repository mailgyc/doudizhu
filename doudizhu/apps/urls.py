from apps.account.views import IndexHandler, LoginHandler, SignupHandler, UserInfoHandler
from apps.game.views import SocketHandler

url_patterns = [
    ('/', IndexHandler),
    ('/login', LoginHandler),
    ('/signup', SignupHandler),
    ('/userinfo', UserInfoHandler),
    ('/ws', SocketHandler),
]
