#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>


class Config:
    split_flag = b'\x00\xff\xff\xff\x00'


class Color:
    Black = 0
    Red = 1
    Blue = 2
    Yellow = 3
    Green = 4


color_map = {
    'black': Color.Black,
    'red': Color.Red,
    'blue': Color.Blue,
    'yellow': Color.Yellow,
    'green': Color.Green
}


class ServerType(str):
    FLASK = 19951
    TORNADO = 19952
    SANIC = 19953


class Response:

    def __init__(self):
        # SIGN
        self.INVALID_PUBLIC_PARAMS = dict(message='Invalid Public Params', code=400001, success=False)
        self.UNKNOWN_SERVER_ERROR = dict(message='Unknown Server Error', code=400002, success=False)
        self.INVALID_TIMESTAMP = dict(message='Invalid Timestamp', code=400004, success=False)
        self.INVALID_ACCESS_KEY = dict(message='Invalid Access Key', code=400005, success=False)
        self.INVALID_QUERY_STRING = dict(message='Invalid Query String', code=400006, success=False)

        # SERVER
        self.SUCCESS = dict(message=None, code=000000, success=True)
        self.INVALID_IMAGE_FORMAT = dict(message='Invalid Image Format', code=500001, success=False)
        self.INVALID_BASE64_STRING = dict(message='Invalid Base64 String', code=500002, success=False)
        self.IMAGE_DAMAGE = dict(message='Image Damage', code=500003, success=False)
        self.IMAGE_SIZE_NOT_MATCH_GRAPH = dict(message='Image Size Not Match Graph Value', code=500004, success=False)

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
