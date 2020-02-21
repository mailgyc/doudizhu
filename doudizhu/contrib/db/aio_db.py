import asyncio
import functools
import logging
from typing import Dict, Union

import aiomysql
from aiomysql import Pool, DictCursor


class AsyncConnection(object):

    def __init__(self, loop=None, **kwargs):
        self._db_args = {
            'host': kwargs.get('host'),
            'db': kwargs.get('database'),
            'user': kwargs.get('user'),
            'password': kwargs.get('password'),
            'port': kwargs.get('port', 3306),
            'minsize': kwargs.get('min_connections', 1),
            'maxsize': kwargs.get('max_connections', 10),
            'cursorclass': DictCursor,
            'autocommit': True,
        }
        self._loop = loop
        self._conn_pool: Pool = None
        self._async_wait = None

    @property
    def loop(self):
        return self._loop or asyncio.get_event_loop()

    async def close(self):
        if self._async_wait:
            await self._async_wait
        if self._conn_pool:
            # self._conn_pool.terminate()
            self._conn_pool.close()
            await self._conn_pool.wait_closed()
            self._async_wait = None
            self._conn_pool = None

    async def reconnect(self):
        if self._conn_pool:
            return
        elif self._async_wait:
            await self._async_wait
        else:
            self._async_wait = self.loop.create_future()
            try:
                self._conn_pool = await aiomysql.create_pool(loop=self.loop, **self._db_args)
                self._async_wait.set_result(True)
            except Exception as e:
                if not self._async_wait.done():
                    self._async_wait.set_exception(e)
                self._async_wait = None
                raise

    async def fetchone(self, query: str, *args, **kwargs) -> Dict[str, Union[int, str]]:
        cursor = await self.cursor()
        try:
            await self._execute(cursor, query, args, kwargs)
            return await cursor.fetchone()
        finally:
            await cursor.release()

    async def insert(self, query: str, *args, **kwargs):
        cursor = await self.cursor()
        try:
            await self._execute(cursor, query, args, kwargs)
            return cursor.lastrowid
        finally:
            await cursor.release()

    async def cursor(self, conn=None) -> aiomysql.Cursor:
        in_transaction = conn is not None
        if not conn:
            if not self._conn_pool:
                await self.reconnect()
            conn = await self._conn_pool.acquire()
        cursor = await conn.cursor()
        cursor.release = functools.partial(self.release_cursor, cursor, in_transaction=in_transaction)
        return cursor

    async def release_cursor(self, cursor, in_transaction=False):
        conn = cursor.connection
        await cursor.close()
        if not in_transaction:
            self._conn_pool.release(conn)

    async def _execute(self, cursor: aiomysql.Cursor, query: str, args, kwargs):
        try:
            return await cursor.execute(query, kwargs or args)
        except aiomysql.OperationalError:
            logging.exception("Error connecting to MySQL on %s", self.host)
            await self.close()
            raise
