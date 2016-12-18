from .redistest import RedisTestCase

import tornadoredis

class Ipv6ConnectionTestCase(RedisTestCase):

    def test_encode(self):
        conn = tornadoredis.connection.Connection('::1')
        try:
            conn.connect()
        except tornadoredis.exceptions.ConnectionError as e:
            msg, = e.args
            bad_error = '[Errno -9] Address family for hostname not supported'
            self.assertNotEqual(bad_error, msg)
