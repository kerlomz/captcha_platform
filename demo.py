#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import io
import os
import base64
import datetime
import hashlib
import time
from config import Config
from requests import Session, post, get
from PIL import Image as PilImage
from constants import ServerType

DEFAULT_HOST = "localhost"


def _image(_path, model_type=None, model_site=None, need_color=None):
    with open(_path, "rb") as f:
        img_bytes = f.read()

    b64 = base64.b64encode(img_bytes).decode()
    return {
        'image': b64,
        'model_type': model_type,
        'model_site': model_site,
        'need_color': need_color,
    }


class Auth(object):

    def __init__(self, host: str, server_type: ServerType, access_key=None, secret_key=None, port=None):
        self._conf = Config(conf_path="config.yaml")
        self._url = 'http://{}:{}/captcha/auth/v2'.format(host, port if port else server_type)
        self._access_key = access_key if access_key else self._conf.access_key
        self._secret_key = secret_key if secret_key else self._conf.secret_key
        self.true_count = 0
        self.total_count = 0

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
        return post(self._url, json=params).json()

    def local_iter(self, image_list: dict):
        for k, v in image_list.items():
            code = self.request(v).get('message')
            _true = str(code).lower() == str(k).lower()
            if _true:
                self.true_count += 1
            self.total_count += 1
            print('result: {}, label: {}, flag: n{}, acc_rate: {}'.format(code, k, _true, self.true_count/self.total_count))


class NoAuth(object):
    def __init__(self, host: str, server_type: ServerType, port=None):
        self._url = 'http://{}:{}/captcha/v1'.format(host, port if port else server_type)
        self.true_count = 0
        self.total_count = 0

    def request(self, params):
        return post(self._url, json=params).json()

    def local_iter(self, image_list: dict):
        for k, v in image_list.items():
            try:
                code = self.request(v).get('message')
                _true = str(code).lower() == str(k).lower()
                if _true:
                    self.true_count += 1
                self.total_count += 1
                print('result: {}, label: {}, flag: {}, acc_rate: {}'.format(
                    code, k, _true, self.true_count/self.total_count
                ))
            except Exception as e:
                print(e)

    def press_testing(self, image_list: dict, model_type=None, model_site=None):
        from multiprocessing.pool import ThreadPool
        pool = ThreadPool(500)
        for k, v in image_list.items():
            pool.apply_async(self.request({"image": v.get('image'), "model_type": model_type, "model_site": model_site}))
        pool.close()
        pool.join()
        print(self.true_count/len(image_list))


class GoogleRPC(object):

    def __init__(self, host: str):
        self._url = '{}:50054'.format(host)
        self.true_count = 0
        self.total_count = 0

    def request(self, image, println=False, value=None, model_type=None, model_site=None):

        import grpc
        import grpc_pb2
        import grpc_pb2_grpc
        channel = grpc.insecure_channel(self._url)
        stub = grpc_pb2_grpc.PredictStub(channel)
        response = stub.predict(grpc_pb2.PredictRequest(
            image=image, split_char=',', model_type=model_type, model_site=model_site
        ))
        if println and value:
            _true = str(response.result).lower() == str(value).lower()
            if _true:
                self.true_count += 1
            print("result: {}, label: {}, flag: {}".format(response.result, value, _true))
        return {"message": response.result, "code": response.code, "success": response.success}

    def local_iter(self, image_list: dict, model_type=None, model_site=None):
        for k, v in image_list.items():
            code = self.request(v.get('image'), model_type=model_type, model_site=model_site).get('message')
            _true = str(code).lower() == str(k).lower()
            if _true:
                self.true_count += 1
            self.total_count += 1
            print('result: {}, label: {}, flag: {}, acc_rate: {}'.format(
                code, k, _true, self.true_count/self.total_count
            ))

    def remote_iter(self, url: str, save_path: str=None, num=100, model_type=None, model_site=None):
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        sess = Session()
        sess.verify = False
        for i in range(num):
            img_bytes = sess.get(url).content
            img_b64 = base64.b64encode(img_bytes).decode()
            code = self.request(img_b64, model_type=model_type, model_site=model_site).get('message')
            with open("{}/{}_{}.jpg".format(save_path, code, hashlib.md5(img_bytes).hexdigest()), "wb") as f:
                f.write(img_bytes)

            print('result: {}'.format(
                code,
            ))

    def press_testing(self, image_list: dict, model_type=None, model_site=None):
        from multiprocessing.pool import ThreadPool
        pool = ThreadPool(500)
        for k, v in image_list.items():
            pool.apply_async(self.request(v.get('image'), True, k, model_type=model_type, model_site=model_site))
        pool.close()
        pool.join()
        print(self.true_count/len(image_list))


if __name__ == '__main__':

    # # Here you can replace it with a web request to get images in real time.
    # with open(r"D:\***.jpg", "rb") as f:
    #     img_bytes = f.read()

    # # Here is the code for the network request.
    # # Replace your own captcha url for testing.
    # # sess = Session()
    # # sess.headers = {
    # #     'user-agent': 'Chrome'
    # # }
    # # img_bytes = sess.get("http://***.com/captcha").content
    #
    # # Open the image for human eye comparison,
    # # preview whether the recognition result is consistent.
    # data_stream = io.BytesIO(img_bytes)
    # pil_image = PilImage.open(data_stream)
    # pil_image.show()
    # api_params = {
    #     'image': base64.b64encode(img_bytes).decode(),
    # }
    # print(api_params)
    # for i in range(1):
        # Tornado API with authentication
        # resp = Auth(DEFAULT_HOST, ServerType.TORNADO).request(api_params)
        # print(resp)

        # Flask API with authentication
        # resp = Auth(DEFAULT_HOST, ServerType.FLASK).request(api_params)
        # print(resp)

        # Tornado API without authentication
        # resp = NoAuth(DEFAULT_HOST, ServerType.TORNADO).request(api_params)
        # print(resp)

        # Flask API without authentication
        # resp = NoAuth(DEFAULT_HOST, ServerType.FLASK).request(api_params)
        # print(resp)

        # API by gRPC - The fastest way.
        # If you want to identify multiple verification codes continuously, please do like this:
        # resp = GoogleRPC(DEFAULT_HOST).request(base64.b64encode(img_bytes+b'\x00\xff\xff\xff\x00'+img_bytes).decode())
        # b'\x00\xff\xff\xff\x00' is the split_flag defined in config.py
        # resp = GoogleRPC(DEFAULT_HOST).request(base64.b64encode(img_bytes).decode())
        # print(resp)
        # pass

    # API by gRPC - The fastest way, Local batch version, only for self testing.
    path = r"F:\TransSet\kap-1"
    path_list = os.listdir(path)
    print(path_list)
    batch = {
        _path.split('_')[0].lower(): _image(
            os.path.join(path, _path),
            model_type=None,
            model_site=None,
            need_color=None,
        )
        for i, _path in enumerate(path_list)
        if i < 1000
    }
    # print(batch)
    NoAuth(DEFAULT_HOST, ServerType.TORNADO).local_iter(batch)
    # NoAuth(DEFAULT_HOST, ServerType.FLASK).local_iter(batch)
    # NoAuth(DEFAULT_HOST, ServerType.SANIC).local_iter(batch)
    # GoogleRPC(DEFAULT_HOST).local_iter(batch, model_site=None, model_type=None)
    # GoogleRPC(DEFAULT_HOST).press_testing(batch, model_site=None, model_type=None)
    # GoogleRPC(DEFAULT_HOST).remote_iter("http://www.***.com/captcha", "D:\****", 100, model_site=None, model_type=None)