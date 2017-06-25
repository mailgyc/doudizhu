import logging
import time

import pymysql


class Connection(object):
    def __init__(self, host, database, user=None, password=None, **kwargs):
        self.host = host
        self.max_idle_time = float(7 * 3600)

        self._db_args = {
            "host": host,
            'database': database,
            "user": user,
            "password": password,
            "port": 3306,

            'charset': 'utf8',
            'use_unicode': True,
            'sql_mode': 'TRADITIONAL',
            'init_command': 'SET time_zone = "+0:00"',
        }

        self._db = None
        self._last_use_time = time.time()
        try:
            self.reconnect()
        except Exception:
            logging.error("Cannot connect to MySQL on %s", self.host, exc_info=True)

    def __del__(self):
        self.close()

    def close(self):
        """Closes this database connection."""
        if getattr(self, "_db", None) is not None:
            self._db.close()
            self._db = None

    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        self.close()
        self._db = pymysql.connect(**self._db_args)
        self._db.autocommit(True)

    def iter(self, query, *args, **kwargs):
        """Returns an iterator for the given query and args."""
        self._ensure_connected()
        cursor = pymysql.cursors.SSCursor(self._db)
        try:
            self._execute(cursor, query, args, kwargs)
            column_names = [d[0] for d in cursor.description]
            for row in cursor:
                yield Row(zip(column_names, row))
        finally:
            cursor.close()

    def query(self, query, *args, **kwargs):
        """Returns a row list for the given query and args."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, args, kwargs)
            column_names = [d[0] for d in cursor.description]
            return [Row(zip(column_names, row)) for row in cursor]
        finally:
            cursor.close()

    def get(self, query, *args, **kwargs):
        """Returns the (singular) row returned by the given query.

        If the query has no results, returns None.  If it has
        more than one result, raises an exception.
        """
        rows = self.query(query, *args, **kwargs)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for Database.get() query")
        else:
            return rows[0]

    def insert(self, query, *args, **kwargs):
        """Executes the given query, returning the last rowid from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, args, kwargs)
            return cursor.lastrowid
        finally:
            cursor.close()

    def update(self, query, *args, **kwargs):
        """Executes the given query, returning the rowcount from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, args, kwargs)
            return cursor.rowcount
        finally:
            cursor.close()

    def execute_many(self, query, args):
        """Executes the given query against all the given param sequences.
        We return the last rowid from the query.
        """
        return self.insert_many(query, args)

    def insert_many(self, query, args):
        """Executes the given query against all the given param sequences.
        We return the last rowid from the query.
        """
        cursor = self._cursor()
        try:
            cursor.execute_many(query, args)
            return cursor.lastrowid
        finally:
            cursor.close()

    def update_many(self, query, args):
        """Executes the given query against all the given param sequences.
        We return the rowcount from the query.
        """
        cursor = self._cursor()
        try:
            cursor.execute_many(query, args)
            return cursor.rowcount
        finally:
            cursor.close()

    def _ensure_connected(self):
        # Mysql by default closes client connections that are idle for
        # 8 hours, but the client library does not report this fact until
        # you try to perform a query and it fails.  Protect against this
        # case by preemptively closing and reopening the connection
        # if it has been idle for too long (7 hours by default).
        if self._db is None or (time.time() - self._last_use_time > self.max_idle_time):
            self.reconnect()
        self._last_use_time = time.time()

    def _cursor(self):
        self._ensure_connected()
        return self._db.cursor()

    def _execute(self, cursor, query, args, kwargs):
        try:
            return cursor.execute(query, kwargs or args)
        except pymysql.OperationalError:
            logging.error("Error connecting to MySQL on %s", self.host)
            self.close()
            raise


class Row(dict):
    """A dict that allows for object-like property access syntax."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
