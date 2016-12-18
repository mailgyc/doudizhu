#!/usr/bin/env python
# -*- coding: utf-8 -*-


class RedisError(Exception):
    pass


class ConnectionError(RedisError):
    pass


class RequestError(RedisError):
    def __init__(self, message, cmd_line=None):
        self.message = message
        self.cmd_line = cmd_line

    def __repr__(self):
        if self.cmd_line:
            return 'RequestError (on %s [%s, %s]): %s' \
                   % (self.cmd_line.cmd, self.cmd_line.args,
                      self.cmd_line.kwargs, self.message)
        return 'RequestError: %s' % self.message

    __str__ = __repr__


class ResponseError(RedisError):
    def __init__(self, message, cmd_line=None):
        self.message = message
        self.cmd_line = cmd_line

    def __repr__(self):
        if self.cmd_line:
            return 'ResponseError (on %s [%s, %s]): %s' \
                   % (self.cmd_line.cmd, self.cmd_line.args,
                      self.cmd_line.kwargs, self.message)
        return 'ResponseError: %s' % self.message

    __str__ = __repr__


class InvalidResponse(RedisError):
    pass


class LockError(RedisError):
    "Errors thrown from the Lock"
    pass
