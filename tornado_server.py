#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import grpc
import grpc_pb2
import grpc_pb2_grpc
import optparse
import tornado.ioloop
from tornado.web import RequestHandler
from logging import basicConfig, INFO
from constants import Response
from json.decoder import JSONDecodeError
from tornado.escape import json_decode, json_encode
from interface import Interface
from config import ModelConfig
from utils import ImageUtils
from signature import Signature, ServerType

sign = Signature(ServerType.TORNADO)


def rpc_request(image):
    channel = grpc.insecure_channel('[::]:50054')
    stub = grpc_pb2_grpc.PredictStub(channel)
    response = stub.predict(grpc_pb2.PredictRequest(captcha_img=image))
    return response.result, response.code, response.success


class BaseHandler(RequestHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.exception = Response()

    def data_received(self, chunk):
        pass

    def parse_param(self):
        try:
            data = json_decode(self.request.body)
        except JSONDecodeError:
            data = self.request.body_arguments
        if not data:
            raise tornado.web.HTTPError(400)
        return data

    def write_error(self, code, **kw):
        system = {
            500: json_encode(dict(code=code, message="Internal Server Error", success=False)),
            400: json_encode(dict(code=code, message="Bad Request", success=False)),
            404: json_encode(dict(code=code, message="404 Not Found", success=False)),
            403: json_encode(dict(code=code, message="Forbidden", success=False)),
            405: json_encode(dict(code=code, message="Method Not Allowed", success=False)),
        }
        return self.finish(system.get(code) if code in system.keys() else json_encode(self.exception.find(code)))


class AuthHandler(BaseHandler):

    @sign.signature_required
    def post(self):
        data = self.parse_param()
        if 'image' not in data.keys():
            raise tornado.web.HTTPError(400)
        split_char = data['split_char'] if 'split_char' in data else interface.model.split_char
        # # You can separate the http service and the gRPC service like this:
        # response = rpc_request(request.json['image'])
        image_batch, response = ImageUtils(interface.model).get_image_batch(data['image'])
        result = interface.predict_byte(image_batch, split_char)
        response['message'] = result
        return self.write(json_encode(response))


class NoAuthHandler(BaseHandler):

    def post(self):
        data = self.parse_param()
        if 'image' not in data.keys():
            raise tornado.web.HTTPError(400)
        split_char = data['split_char'] if 'split_char' in data else interface.model.split_char
        # # You can separate the http service and the gRPC service like this:
        # response = rpc_request(request.json['image'])
        image_batch, response = ImageUtils(interface.model).get_image_batch(data['image'])
        result = interface.predict_byte(image_batch, split_char)
        response['message'] = result
        return self.write(json_encode(response))


def make_app():
    return tornado.web.Application([
        (r"/captcha/auth/v2", AuthHandler),
        (r"/captcha/v1", NoAuthHandler),
        (r".*", BaseHandler),
    ])


if __name__ == "__main__":
    basicConfig(level=INFO)

    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=19952, dest="port")
    parser.add_option('-m', '--config', type="str", default='model.yaml', dest="config")
    parser.add_option('-a', '--path', type="str", default='model', dest="model_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    model_conf = opt.config
    model_path = opt.model_path

    model = ModelConfig(model_conf=model_conf, model_path=model_path)
    sign.set_auth([{'accessKey': model.access_key, 'secretKey': model.secret_key}])
    interface = Interface(model)

    server_host = "0.0.0.0"
    print('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app()
    app.listen(server_port, server_host)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
