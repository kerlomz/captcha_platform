#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

from functools import wraps

from flask import request

from constants import RequestException
from exception import *
from utils import *


class Signature(object):
    """ 接口签名认证 """

    def __init__(self):
        self._except = RequestException()
        self._auth = []
        self._timestamp_expiration = 120

    def set_auth(self, auth):
        self._auth = auth

    def _check_req_timestamp(self, req_timestamp):
        """ 校验时间戳
        @pram req_timestamp str,int: 请求参数中的时间戳(10位)
        """
        if len(str(req_timestamp)) == 10:
            req_timestamp = int(req_timestamp)
            now_timestamp = Sign.timestamp()
            if now_timestamp - self._timestamp_expiration <= req_timestamp <= now_timestamp + self._timestamp_expiration:
                return True
        return False

    def _check_req_access_id(self, req_access_key):
        """ 校验access_id
        @pram req_access_id str: 请求参数中的用户标识id
        """
        if req_access_key in [i['accessKey'] for i in self._auth if "accessKey" in i]:
            return True
        return False

    def _get_secret_key(self, access_key):
        """ 根据access_id获取对应的secret_key
        @pram access_id str: 用户标识id
        """
        return [i['secretKey'] for i in self._auth if i.get('accessKey') == access_key][0]

    def _sign(self, args):
        """ MD5签名
        @param args: 除signature外请求的所有查询参数(公共参数和私有参数)
        """
        if "sign" in args:
            args.pop("sign")
        access_key = args["accessKey"]
        query_string = '&'.join(['{}={}'.format(k, v) for (k, v) in sorted(args.items())])
        query_string = '&'.join([query_string, self._get_secret_key(access_key)])
        return Sign.md5(query_string).upper()

    def _verification(self, req_params):
        """ 校验请求是否有效
        @param req_params: 请求的所有查询参数(公共参数和私有参数)
        """
        try:
            req_signature = req_params["sign"]
            req_timestamp = req_params["timestamp"]
            req_access_key = req_params["accessKey"]
        except KeyError:
            raise InvalidUsage(**self._except.INVALID_PUBLIC_PARAMS)
        except Exception:
            raise InvalidUsage(**self._except.UNKNOWN_SERVER_ERROR)
        else:
            # NO.1 校验时间戳
            if not self._check_req_timestamp(req_timestamp):
                raise InvalidUsage(**self._except.INVALID_TIMESTAMP)
            # NO.2 校验access_id
            if not self._check_req_access_id(req_access_key):
                raise InvalidUsage(**self._except.INVALID_ACCESS_KEY)
            # NO.3 校验sign
            if req_signature == self._sign(req_params):
                return True
            else:
                raise InvalidUsage(**self._except.INVALID_QUERY_STRING)

    def signature_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            params = request.json
            result = self._verification(params)
            if result is True:
                return f(*args, **kwargs)

        return decorated_function
