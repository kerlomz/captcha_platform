#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import time
import json
import optparse
import threading
import tornado.ioloop
import tornado.log
import tornado.gen
import tornado.httpserver
from tornado.web import RequestHandler
from constants import Response
from json.decoder import JSONDecodeError
from tornado.escape import json_decode, json_encode
from interface import InterfaceManager, Interface
from config import Config
from utils import ImageUtils, ParamUtils, Arithmetic
from signature import Signature, ServerType
from watchdog.observers import Observer
from event_handler import FileEventHandler
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from middleware import *

sign = Signature(ServerType.TORNADO)
arithmetic = Arithmetic()


class BaseHandler(RequestHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.exception = Response()
        self.executor = ThreadPoolExecutor(workers)

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


class NoAuthHandler(BaseHandler):

    @run_on_executor
    def predict(self, interface: Interface, image_batch, split_char, size_string, model_type, model_site, start_time):
        result = interface.predict_batch(image_batch, split_char)
        if interface.model_charset == 'ARITHMETIC':
            if '=' in result or '+' in result or '-' in result or '×' in result or '÷' in result:
                result = result.replace("×", "*").replace("÷", "/")
                result = str(int(arithmetic.calc(result)))
        logger.info('[{} {}] | [{}] - Size[{}] - Type[{}] - Site[{}] - Predict[{}] - {} ms'.format(
            self.request.remote_ip, self.request.uri, interface.name, size_string, model_type, model_site, result,
            round((time.time() - start_time) * 1000))
        )

        return result

    @tornado.gen.coroutine
    def post(self):
        start_time = time.time()
        data = self.parse_param()
        if 'image' not in data.keys():
            raise tornado.web.HTTPError(400)

        model_type = ParamUtils.filter(data.get('model_type'))
        model_site = ParamUtils.filter(data.get('model_site'))
        model_name = ParamUtils.filter(data.get('model_name'))
        split_char = ParamUtils.filter(data.get('split_char'))
        need_color = ParamUtils.filter(data.get('need_color'))
        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode({"message": "", "success": False, "code": -999}))
        bytes_batch, response = ImageUtils.get_bytes_batch(data['image'])

        if not bytes_batch:
            logger.error('[{} {}] | Type[{}] - Site[{}] - Response[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, model_type, model_site, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])
        if 'model_site' in data and data['model_site']:
            interface = interface_manager.get_by_sites(model_site, size_string, strict=system_config.strict_sites)
        elif 'model_type' in data and data['model_type']:
            interface = interface_manager.get_by_type_size(size_string, model_type)
        elif 'model_name' in data and data['model_name']:
            interface = interface_manager.get_by_name(model_name)
        else:
            interface = interface_manager.get_by_size(size_string)
        if not interface:
            logger.info('Service is not ready!')
            return self.finish(json_encode({"message": "", "success": False, "code": 999}))

        split_char = split_char if 'split_char' in data else interface.model_conf.split_char

        if need_color:
            bytes_batch = [color_extract.separate_color(_, color_map[need_color]) for _ in bytes_batch]

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            logger.error('[{} {}] | [{}] - Size[{}] - Type[{}] - Site[{}] - Response[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, interface.name, size_string, model_type, model_site, response,
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(response))
        response['message'] = yield self.predict(interface, image_batch, split_char, size_string, model_type, model_site, start_time)
        return self.finish(json_encode(response))


class AuthHandler(NoAuthHandler):

    @sign.signature_required
    def post(self):
        return super().post()


class SimpleHandler(BaseHandler):

    def post(self):
        start_time = time.time()

        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode({"message": "", "success": False, "code": -999}))

        bytes_batch, response = ImageUtils.get_bytes_batch(self.request.body)

        if not bytes_batch:
            logger.error('Response[{}] - {} ms'.format(
                response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])

        interface = interface_manager.get_by_size(size_string)
        if not interface:
            logger.info('Service is not ready!')
            return self.finish(json_encode({"message": "", "success": False, "code": 999}))

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            logger.error('[{}] - Size[{}] - Response[{}] - {} ms'.format(
                interface.name, size_string, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        result = interface.predict_batch(image_batch, None)
        logger.info('[{}] - Size[{}] - Predict[{}] - {} ms'.format(
            interface.name, size_string, result, (time.time() - start_time) * 1000)
        )
        response['message'] = result
        return self.write(json_encode(response))


class ServiceHandler(BaseHandler):

    def get(self):
        response = {
            "total": interface_manager.total,
            "online": interface_manager.online_names,
            "support": interface_manager.support_sites,
            "invalid": interface_manager.invalid_group
        }
        return self.finish(json.dumps(response, ensure_ascii=False, indent=2))


class FileHandler(tornado.web.StaticFileHandler):
    def data_received(self, chunk):
        pass

    def set_extra_headers(self, path):
        self.set_header("Cache-control", "no-cache")


def make_app():
    return tornado.web.Application([
        (r"/captcha/auth/v2", AuthHandler),
        (r"/captcha/v1", NoAuthHandler),
        (r"/captcha/v3", SimpleHandler),
        (r"/service/info", ServiceHandler),
        (r"/service/logs/(.*)", FileHandler, {"path": "logs"}),
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
    parser.add_option('-w', '--workers', type="int", default=50, dest="workers")
    parser.add_option('-c', '--config', type="str", default='./config.yaml', dest="config")
    parser.add_option('-m', '--model_path', type="str", default='model', dest="model_path")
    parser.add_option('-g', '--graph_path', type="str", default='graph', dest="graph_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    conf_path = opt.config
    model_path = opt.model_path
    graph_path = opt.graph_path
    workers = opt.workers

    system_config = Config(conf_path=conf_path, model_path=model_path, graph_path=graph_path)
    logger = system_config.logger
    tornado.log.enable_pretty_logging(logger=logger)
    interface_manager = InterfaceManager()
    threading.Thread(target=event_loop).start()

    sign.set_auth([{'accessKey': system_config.access_key, 'secretKey': system_config.secret_key}])

    server_host = "0.0.0.0"
    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.bind(server_port, server_host)
    http_server.start(1)
    # app.listen(server_port, server_host)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()
