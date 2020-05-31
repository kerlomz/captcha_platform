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
            "SplitFlag": b'\x99\x99\x99\x00\xff\xff\xff\x00\x99\x99\x99',
            "SavePath": "",
            "RequestCountInterval": 86400,
            "GlobalRequestCountInterval": 86400,
            "RequestLimit": -1,
            "GlobalRequestLimit": -1,
            "WithoutLogger": False
        },
        "RouteMap": default_route,
        "Security": {
            "AccessKey": "",
            "SecretKey": ""
        },
        "RequestDef": {
            "InputData": "image",
            "ModelName": "model_name",
        },
        "ResponseDef": {
            "Message": "message",
            "StatusCode": "code",
            "StatusBool": "success",
            "Uid": "uid",
        },
    }


class ServerType(str):
    FLASK = 19951
    TORNADO = 19952
    SANIC = 19953


class Response:

    def __init__(self, def_map: dict):
        # SIGN
        self.INVALID_PUBLIC_PARAMS = dict(Message='Invalid Public Params', StatusCode=400001, StatusBool=False)
        self.UNKNOWN_SERVER_ERROR = dict(Message='Unknown Server Error', StatusCode=400002, StatusBool=False)
        self.INVALID_TIMESTAMP = dict(Message='Invalid Timestamp', StatusCode=400004, StatusBool=False)
        self.INVALID_ACCESS_KEY = dict(Message='Invalid Access Key', StatusCode=400005, StatusBool=False)
        self.INVALID_QUERY_STRING = dict(Message='Invalid Query String', StatusCode=400006, StatusBool=False)

        # SERVER
        self.SUCCESS = dict(Message=None, StatusCode=000000, StatusBool=True)
        self.INVALID_IMAGE_FORMAT = dict(Message='Invalid Image Format', StatusCode=500001, StatusBool=False)
        self.INVALID_BASE64_STRING = dict(Message='Invalid Base64 String', StatusCode=500002, StatusBool=False)
        self.IMAGE_DAMAGE = dict(Message='Image Damage', StatusCode=500003, StatusBool=False)
        self.IMAGE_SIZE_NOT_MATCH_GRAPH = dict(Message='Image Size Not Match Graph Value', StatusCode=500004, StatusBool=False)

        self.INVALID_PUBLIC_PARAMS = self.parse(self.INVALID_PUBLIC_PARAMS, def_map)
        self.UNKNOWN_SERVER_ERROR = self.parse(self.UNKNOWN_SERVER_ERROR, def_map)
        self.INVALID_TIMESTAMP = self.parse(self.INVALID_TIMESTAMP, def_map)
        self.INVALID_ACCESS_KEY = self.parse(self.INVALID_ACCESS_KEY, def_map)
        self.INVALID_QUERY_STRING = self.parse(self.INVALID_QUERY_STRING, def_map)

        self.SUCCESS = self.parse(self.SUCCESS, def_map)
        self.INVALID_IMAGE_FORMAT = self.parse(self.INVALID_IMAGE_FORMAT, def_map)
        self.INVALID_BASE64_STRING = self.parse(self.INVALID_BASE64_STRING, def_map)
        self.IMAGE_DAMAGE = self.parse(self.IMAGE_DAMAGE, def_map)
        self.IMAGE_SIZE_NOT_MATCH_GRAPH = self.parse(self.IMAGE_SIZE_NOT_MATCH_GRAPH, def_map)

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

    @staticmethod
    def parse(src: dict, target_map: dict):
        return {target_map[k]: v for k, v in src.items()}
