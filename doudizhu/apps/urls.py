from apps.account.views import IndexHandler, LoginHandler, UserInfoHandler
from apps.game.views import SocketHandler
from apps.social.views import WeChatConfig, AuthHandler

url_patterns = [
    ('/', IndexHandler),
    ('/login', LoginHandler),
    ('/userinfo', UserInfoHandler),
    ('/ws', SocketHandler),
    ('/social/config', WeChatConfig),
    ('/social/index', AuthHandler),
]
