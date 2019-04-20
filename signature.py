#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
from functools import wraps
from constants import ServerType
from utils import *


class InvalidUsage(Exception):

    def __init__(self, message, code=None):
        Exception.__init__(self)
        self.message = message
        self.success = False
        self.code = code

    def to_dict(self):
        rv = {'code': self.code, 'message': self.message, 'success': self.success}
        return rv


class Signature(object):
    """ api signature authentication """

    def __init__(self, server_type: ServerType):
        self._except = Response()
        self._auth = []
        self._timestamp_expiration = 120
        self.request = None
        self.type = server_type

    def set_auth(self, auth):
        self._auth = auth

    def _check_req_timestamp(self, req_timestamp):
        """ Check the timestamp
        @pram req_timestamp str,int: Timestamp in the request parameter (10 digits)
        """
        if len(str(req_timestamp)) == 10:
            req_timestamp = int(req_timestamp)
            now_timestamp = SignUtils.timestamp()
            if now_timestamp - self._timestamp_expiration <= req_timestamp <= now_timestamp + self._timestamp_expiration:
                return True
        return False

    def _check_req_access_key(self, req_access_key):
        """ Check the access_key in the request parameter
        @pram req_access_key str: access key in the request parameter
        """
        if req_access_key in [i['accessKey'] for i in self._auth if "accessKey" in i]:
            return True
        return False

    def _get_secret_key(self, access_key):
        """ Obtain the corresponding secret_key according to access_key
        @pram access_key str: access key in the request parameter
        """
        secret_keys = [i['secretKey'] for i in self._auth if i.get('accessKey') == access_key]
        return "" if not secret_keys else secret_keys[0]

    def _sign(self, args):
        """ MD5 signature
        @param args: All query parameters (public and private) requested in addition to signature
        """
        if "sign" in args:
            args.pop("sign")
        access_key = args["accessKey"]
        query_string = '&'.join(['{}={}'.format(k, v) for (k, v) in sorted(args.items())])
        query_string = '&'.join([query_string, self._get_secret_key(access_key)])
        return SignUtils.md5(query_string).upper()

    def _verification(self, req_params, tornado_handler=None):
        """ Verify that the request is valid
        @param req_params: All query parameters requested (public and private)
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
            if self.type == ServerType.FLASK or self.type == ServerType.SANIC:
                from flask.app import HTTPException, json
                # NO.1 Check the timestamp
                if not self._check_req_timestamp(req_timestamp):
                    raise HTTPException(response=json.jsonify(self._except.INVALID_TIMESTAMP))
                # NO.2 Check the access_id
                if not self._check_req_access_key(req_access_key):
                    raise HTTPException(response=json.jsonify(self._except.INVALID_ACCESS_KEY))
                # NO.3 Check the sign
                if req_signature == self._sign(req_params):
                    return True
                else:
                    raise HTTPException(response=json.jsonify(self._except.INVALID_QUERY_STRING))
            elif self.type == ServerType.TORNADO:
                from tornado.web import HTTPError
                # NO.1 Check the timestamp
                if not self._check_req_timestamp(req_timestamp):
                    return tornado_handler.write_error(self._except.INVALID_TIMESTAMP['code'])
                # NO.2 Check the access_id
                if not self._check_req_access_key(req_access_key):
                    return tornado_handler.write_error(self._except.INVALID_ACCESS_KEY['code'])
                # NO.3 Check the sign
                if req_signature == self._sign(req_params):
                    return True
                else:
                    return tornado_handler.write_error(self._except.INVALID_QUERY_STRING['code'])
            raise Exception('Unknown Server Type')

    def signature_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if self.type == ServerType.FLASK:
                from flask import request
                params = request.json
            elif self.type == ServerType.TORNADO:
                from tornado.escape import json_decode
                params = json_decode(args[0].request.body)
            elif self.type == ServerType.SANIC:
                params = args[0].json
            else:
                raise UserWarning('Illegal type, the current version is not supported at this time.')
            result = self._verification(params, args[0] if self.type == ServerType.TORNADO else None)
            if result is True:
                return f(*args, **kwargs)
        return decorated_function
