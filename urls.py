from handlers.socket import SocketHandler
from handlers.web import WebHandler, UpdateHandler, RegHandler

url_patterns = [
    (r'/', WebHandler),
    (r'/update', UpdateHandler),
    (r'/reg', RegHandler),
    (r'/ws', SocketHandler),
]
