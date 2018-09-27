#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import socket
import uuid


class ServerType(str):
    FLASK = 'FLASK'
    TORNADO = 'TORNADO'


class RequestException:

    def __init__(self):
        # SIGN
        self.INVALID_PUBLIC_PARAMS = dict(message='Invalid Public Params', code=40001, success=False)
        self.UNKNOWN_SERVER_ERROR = dict(message='Unknown Server Error', code=40002, success=False)
        self.INVALID_TIMESTAMP = dict(message='Invalid Timestamp', code=40004, success=False)
        self.INVALID_ACCESS_KEY = dict(message='Invalid Access Key', code=40005, success=False)
        self.INVALID_QUERY_STRING = dict(message='Invalid Query String', code=40006, success=False)

        # G-RPC
        self.INVALID_IMAGE_FORMAT = dict(message='Invalid Image Format', code=50001, success=False)
        self.INVALID_BASE64_STRING = dict(message='Invalid Base64 String', code=50002, success=False)
        self.IMAGE_DAMAGE = dict(message='Image Damage', code=50003, success=False)
        self.IMAGE_SIZE_NOT_MATCH_GRAPH = dict(message='Image Size Not Match Graph Value', code=50004, success=False)

    def find_message(self, _code):
        e = [value for value in vars(self).values()]
        _t = [i['message'] for i in e if i['code'] == _code]
        return _t[0] if _t else None

    def find(self, _code):
        e = [value for value in vars(self).values()]
        _t = [i for i in e if i['code'] == _code]
        return _t[0] if _t else None

    def all_code(self):
        return [i['message'] for i in [value for value in vars(self).values()]]
