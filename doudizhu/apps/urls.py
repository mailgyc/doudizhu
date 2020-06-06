from apps.account.views import IndexHandler, LoginHandler, UserInfoHandler
from apps.game.views import SocketHandler
from apps.social.views import WechatConfig, WechatHandler

url_patterns = [
    ('/', IndexHandler),
    ('/login', LoginHandler),
    ('/userinfo', UserInfoHandler),
    ('/ws', SocketHandler),
    ('/social/config', WechatConfig),
    ('/social/index', WechatHandler),
]
