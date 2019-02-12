from apps.account.views import HomeHandler, SignupHandler, LoginHandler
from apps.game.views import SocketHandler

url_patterns = [
    (r'/', HomeHandler),
    (r'/reg', SignupHandler),
    (r'/login', LoginHandler),
    (r'/ws', SocketHandler),
]
