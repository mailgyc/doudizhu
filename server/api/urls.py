from api.auth import IndexHandler, LoginHandler, UserInfoHandler
from api.game.views import SocketHandler
from api.wx import WechatConfig, WechatHandler

url_patterns = [
    ('/', IndexHandler),
    ('/login', LoginHandler),
    ('/userinfo', UserInfoHandler),
    ('/ws', SocketHandler),
    ('/social/config', WechatConfig),
    ('/social/index', WechatHandler),
]
