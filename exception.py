#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>


class InvalidUsage(Exception):

    def __init__(self, message, code=None):
        Exception.__init__(self)
        self.message = message
        self.success = False
        self.code = code

    def to_dict(self):
        rv = {'code': self.code, 'message': self.message, 'success': self.success}
        return rv


def exception(text, code=-1):
    print(text)
    input()
    exit(code)
