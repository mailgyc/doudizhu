from handlers.socket import SocketHandler
from handlers.web import WebHandler, RegHandler

url_patterns = [
    (r'/', WebHandler),
    (r'/reg', RegHandler),
    (r'/ws', SocketHandler),
]
