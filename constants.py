#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import socket
import uuid


class Variable:
    import os
    import sys
    EXEC_PATH = os.path.realpath(sys.argv[0])
    MAC_ADDRESS = ":".join([(uuid.UUID(int=uuid.getnode()).hex[-12:])[e:e + 2] for e in range(0, 11, 2)]).upper()
    HOST_NAME = socket.gethostname()


class RequestException:

    def __init__(self):
        # SIGN
        self.INVALID_PUBLIC_PARAMS = dict(message='Invalid Public Params', code=40001)
        self.UNKNOWN_SERVER_ERROR = dict(message='Unknown Server Error', code=40002)
        self.INVALID_VERSION = dict(message='Invalid Version', code=40003)
        self.INVALID_TIMESTAMP = dict(message='Invalid Timestamp', code=40004)
        self.INVALID_ACCESS_KEY = dict(message='Invalid Access Key', code=40005)
        self.INVALID_QUERY_STRING = dict(message='Invalid Query String', code=40006)

        # FLASK
        self.PARAMETER_MISSING = dict(message='Parameter Missing', code=40007)
        self.DATABASE_CONNECTION_ERROR = dict(message='Database Connection Error', code=40008)
        self.USER_OR_MODEL_DOES_NOT_EXIST = dict(message='User or Model doesn\'t Exist', code=40009)
        self.INSUFFICIENT_BALANCE = dict(message='Insufficient Balance', code=40010)
        self.USER_DOES_NOT_EXIST_OR_BE_BANNED = dict(message='User doesn\'t Exist or be Banned', code=40011)
        self.ORDER_DOES_NOT_EXIST_OR_INVALID = dict(message='Order doesn\'t Exist or Invalid', code=40012)

        # G-RPC
        self.INVALID_IMAGE_FORMAT = dict(message='Invalid Image Format', code=50001)
        self.INVALID_BASE64_STRING = dict(message='Invalid Base64 String', code=50002)
        self.IMAGE_DAMAGE = dict(message='Image Damage', code=50003)

    def find(self, _code):
        e = [value for value in vars(self).values()]
        _t = [i['message'] for i in e if i['code'] == _code]
        return _t[0] if _t else None
