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
from interface import Interface, InterfaceManager
from config import ModelConfig
from utils import ImageUtils
from signature import Signature, ServerType
from graph_session import GraphSessionPool, GraphSession

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
        bytes_batch, response = ImageUtils.get_bytes_batch(data['image'])

        if not bytes_batch:
            self.write(json_encode(response))

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        interface = interface_manager.get_by_size("{}x{}".format(image_size[1], image_size[0]))

        split_char = data['split_char'] if 'split_char' in data else interface.model_conf.split_char

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            return self.write(json_encode(response))

        result = interface.predict_batch(image_batch, split_char)
        response['message'] = result
        return self.write(json_encode(response))


class NoAuthHandler(BaseHandler):

    def post(self):
        data = self.parse_param()
        if 'image' not in data.keys():
            raise tornado.web.HTTPError(400)

        # # You can separate the http service and the gRPC service like this:
        # response = rpc_request(request.json['image'])
        bytes_batch, response = ImageUtils.get_bytes_batch(data['image'])

        if not bytes_batch:
            self.write(json_encode(response))

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        interface = interface_manager.get_by_size("{}x{}".format(image_size[1], image_size[0]))

        split_char = data['split_char'] if 'split_char' in data else interface.model_conf.split_char

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            return self.write(json_encode(response))

        result = interface.predict_batch(image_batch, split_char)
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

    default_model = ModelConfig(model_conf=model_conf, model_path=model_path)
    default_session = GraphSession(default_model)
    session_pool = GraphSessionPool(default_session)
    default_interface = Interface(default_model, session_pool)
    interface_manager = InterfaceManager(default_interface)

    sign.set_auth([{'accessKey': default_model.access_key, 'secretKey': default_model.secret_key}])

    # Example of loading multiple models at the same time
    # - TODO This will be designed as a hot swapping, similar to the TensorFlow-Serving mode of operation.
    # for model_conf in [ModelConfig(model_conf="model.yaml", model_path=model_path)]:
    #     graph_sess = GraphSession(model_conf)
    #     session_pool.add(graph_sess)
    #     interface = Interface(model_conf, session_pool)
    #     interface_manager.add(interface)

    server_host = "0.0.0.0"
    print('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app()
    app.listen(server_port, server_host)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
