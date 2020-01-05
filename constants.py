#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
from enum import Enum, unique


@unique
class ModelScene(Enum):
    """模型场景枚举"""
    Classification = 'Classification'


@unique
class ModelField(Enum):
    """模型类别枚举"""
    Image = 'Image'
    Text = 'Text'


class SystemConfig:
    split_flag = b'\x99\x99\x99\x00\xff\xff\xff\x00\x99\x99\x99'
    default_route = [
            {
                "Class": "AuthHandler",
                "Route": "/captcha/auth/v2"
            },
            {
                "Class": "NoAuthHandler",
                "Route": "/captcha/v1"
            },
            {
                "Class": "SimpleHandler",
                "Route": "/captcha/v3"
            },
            {
                "Class": "HeartBeatHandler",
                "Route": "/check_backend_active.html"
            },
            {
                "Class": "HeartBeatHandler",
                "Route": "/verification"
            },
            {
                "Class": "HeartBeatHandler",
                "Route": "/"
            },
            {
                "Class": "ServiceHandler",
                "Route": "/service/info"
            },
            {
                "Class": "FileHandler",
                "Route": "/service/logs/(.*)",
                "Param": {"path": "logs"}
            },
            {
                "Class": "BaseHandler",
                "Route": ".*"
            }
        ]
    default_config = {
        "System": {
            "DefaultModel": "default",
            "SplitFlag": b'\x99\x99\x99\x00\xff\xff\xff\x00\x99\x99\x99'
        },
        "RouteMap": default_route,
        "Security": {
            "AccessKey": "",
            "SecretKey": ""
        }
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
