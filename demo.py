#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import base64
import datetime
import hashlib
import time

import requests


class Auth(object):

    def __init__(self):
        self._url = 'http://localhost:19951/captcha/auth/v2'
        self._access_key = "C180130204197838"
        self._secret_key = "62d7eb0d370e603acd651066236c878b"

    def sign(self, args):
        """ MD5 signature
        @param args: All query parameters (public and private) requested in addition to signature
        {
            'image': 'base64 encoded text',
            'accessKey': 'C180130204197838',
            'timestamp': 1536682949,
            'sign': 'F641778AE4F93DAF5CCE3E43A674C34E'
        }
        The sign is the md5 encrypted of "accessKey=your_assess_key&image=base64_encoded_text&timestamp=current_timestamp"
        """
        if "sign" in args:
            args.pop("sign")
        query_string = '&'.join(['{}={}'.format(k, v) for (k, v) in sorted(args.items())])
        query_string = '&'.join([query_string, self._secret_key])
        return hashlib.md5(query_string.encode('utf-8')).hexdigest().upper()

    def make_json(self, params):
        if not isinstance(params, dict):
            raise TypeError("params is not a dict")
        # Get the current timestamp
        timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
        # Set public parameters
        params.update(accessKey=self._access_key, timestamp=timestamp)
        params.update(sign=self.sign(params))
        return params

    def request(self, params):
        params = dict(params, **self.make_json(params))
        return requests.post(self._url, json=params)


class NoAuth(object):
    def __init__(self):
        self._url = 'http://localhost:19951/captcha/v1'

    def request(self, params):
        return requests.post(self._url, json=params)


class gRPC(object):

    def __init__(self):
        self._url = 'localhost:50054'

    def request(self, image):
        import grpc
        import grpc_pb2
        import grpc_pb2_grpc
        channel = grpc.insecure_channel(self._url)
        stub = grpc_pb2_grpc.PredictStub(channel)
        print('G-RPC Request Start--')
        response = stub.predict(grpc_pb2.PredictRequest(captcha_img=image))
        print('G-RPC Request End--')
        return {"message": {"result": response.result}, "code": response.code, "success": response.success}


if __name__ == '__main__':

    # Here you can replace it with a web request to get images in real time.

    with open(r"E:\Task\Trains\patchca\2ck8_143247.jpg", "rb") as f:
        img_bytes = f.read()

    api_params = {
        'image': base64.b64encode(img_bytes).decode(),
    }

    for i in range(1000):
        # API with authentication
        resp = Auth().request(api_params)
        print(resp.json())

        # API without authentication
        resp = NoAuth().request(api_params)
        print(resp.json())

        # API by gRPC - The fastest way.
        resp = gRPC().request(base64.b64encode(img_bytes).decode())
        print(resp)
