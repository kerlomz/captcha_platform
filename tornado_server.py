#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import time
import grpc
import grpc_pb2
import grpc_pb2_grpc
import optparse
import threading
import tornado.ioloop
from tornado.web import RequestHandler
from logging import basicConfig, INFO
from constants import Response
from json.decoder import JSONDecodeError
from tornado.escape import json_decode, json_encode
from interface import InterfaceManager
from config import Config
from utils import ImageUtils
from signature import Signature, ServerType
from watchdog.observers import Observer
from event_handler import FileEventHandler

sign = Signature(ServerType.TORNADO)


def rpc_request(image, model_name="", model_type=""):
    channel = grpc.insecure_channel('127.0.0.1:50054')
    stub = grpc_pb2_grpc.PredictStub(channel)
    response = stub.predict(grpc_pb2.PredictRequest(
        image=image,
        split_char=',',
        model_name=model_name,
        model_type=model_type
    ))
    return {"message": response.result, "code": response.code, "success": response.success}


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
        size_string = "{}x{}".format(image_size[1], image_size[0])
        if 'model_type' in data:
            interface = interface_manager.get_by_type_size(size_string, data['model_type'])
        elif 'model_name' in data:
            interface = interface_manager.get_by_name(data['model_name'])
        else:
            interface = interface_manager.get_by_size(size_string)

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
        # response = rpc_request(
        #     data['image'],
        #     data['model_name'] if 'model_name' in data else '',
        #     data['model_type'] if 'model_type' in data else ''
        # )

        bytes_batch, response = ImageUtils.get_bytes_batch(data['image'])

        if not bytes_batch:
            self.write(json_encode(response))

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[1], image_size[0])
        if 'model_type' in data:
            interface = interface_manager.get_by_type_size(size_string, data['model_type'])
        elif 'model_name' in data:
            interface = interface_manager.get_by_name(data['model_name'])
        else:
            interface = interface_manager.get_by_size(size_string)

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


def event_loop():
    observer = Observer()
    event_handler = FileEventHandler(system_config, model_path, interface_manager)
    observer.schedule(event_handler, event_handler.model_conf_path, True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":

    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=19952, dest="port")
    parser.add_option('-c', '--config', type="str", default='./config.yaml', dest="config")
    parser.add_option('-m', '--model_path', type="str", default='model', dest="model_path")
    parser.add_option('-g', '--graph_path', type="str", default='graph', dest="graph_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    conf_path = opt.config
    model_path = opt.model_path
    graph_path = opt.graph_path

    system_config = Config(conf_path=conf_path, model_path=model_path, graph_path=graph_path)
    logger = system_config.logger
    interface_manager = InterfaceManager()
    threading.Thread(target=event_loop).start()

    sign.set_auth([{'accessKey': system_config.access_key, 'secretKey': system_config.secret_key}])

    server_host = "0.0.0.0"
    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app()
    app.listen(server_port, server_host)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
