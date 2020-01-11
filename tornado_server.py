#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import time
import json
import numpy as np
import asyncio
import optparse
import threading
import tornado.ioloop
import tornado.log
import tornado.gen
import tornado.httpserver
import tornado.options
from tornado.web import RequestHandler
from constants import Response
from json.decoder import JSONDecodeError
from tornado.escape import json_decode, json_encode
from interface import InterfaceManager, Interface
from config import Config
from utils import ImageUtils, ParamUtils, Arithmetic
from signature import Signature, ServerType
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from middleware import *
from event_loop import event_loop

tornado.options.define('request_count', default=dict(), type=dict)
model_path = "model"
system_config = Config(conf_path="config.yaml", model_path=model_path, graph_path="graph")
sign = Signature(ServerType.TORNADO, system_config)
arithmetic = Arithmetic()
semaphore = asyncio.Semaphore(500)


class BaseHandler(RequestHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.exception = Response(system_config.response_def_map)
        self.executor = ThreadPoolExecutor(workers)
        self.image_utils = ImageUtils(system_config)

    def data_received(self, chunk):
        pass

    def parse_param(self):
        try:
            data = json_decode(self.request.body)
        except JSONDecodeError:
            data = self.request.body_arguments
        except UnicodeDecodeError:
            raise tornado.web.HTTPError(401)
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

    message_key: str = system_config.response_def_map['Message']
    status_bool_key = system_config.response_def_map['StatusBool']
    status_code_key = system_config.response_def_map['StatusCode']

    @run_on_executor
    def predict(self, interface: Interface, image_batch, split_char, size_string, start_time, log_params, request_count):
        result = interface.predict_batch(image_batch, split_char)
        if interface.model_category == 'ARITHMETIC':
            if '=' in result or '+' in result or '-' in result or '×' in result or '÷' in result:
                result = result.replace("×", "*").replace("÷", "/")
                result = str(int(arithmetic.calc(result)))
        logger.info('[{} {}] | [{}] - Size[{}]{}{} - Predict[{}] - {} ms'.format(
            self.request.remote_ip, self.request.uri, interface.name, size_string, request_count, log_params, result,
            round((time.time() - start_time) * 1000))
        )

        return result

    @property
    def request_incr(self):
        if self.request.remote_ip not in tornado.options.options.request_count:
            tornado.options.options.request_count[self.request.remote_ip] = 1
        else:
            tornado.options.options.request_count[self.request.remote_ip] += 1
        return tornado.options.options.request_count[self.request.remote_ip]

    @tornado.gen.coroutine
    def post(self):
        start_time = time.time()
        data = self.parse_param()
        request_def_map = system_config.request_def_map
        input_data_key = request_def_map['InputData']
        model_name_key = request_def_map['ModelName']
        if input_data_key not in data.keys():
            raise tornado.web.HTTPError(400)

        model_name = ParamUtils.filter(data.get(model_name_key))
        output_split = ParamUtils.filter(data.get('output_split'))
        need_color = ParamUtils.filter(data.get('need_color'))
        param_key = ParamUtils.filter(data.get('param_key'))

        request_incr = self.request_incr
        request_count = " - Count[{}]".format(request_incr)
        log_params = " - ParamKey[{}]".format(param_key) if param_key else ""
        log_params += " - NeedColor[{}]".format(need_color) if need_color else ""

        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode(
                {self.message_key: "", self.status_bool_key: False, self.status_code_key: -999}
            ))
        bytes_batch, response = self.image_utils.get_bytes_batch(data[input_data_key])

        if not bytes_batch:
            logger.error('[{} {}] | - Response[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))
        auxiliary_result = None

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])

        if request_limit != -1 and request_incr > request_limit:
            logger.info('[{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, size_string, request_count, log_params,
                "Maximum number of requests exceeded",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode({
                self.message_key: "The maximum number of requests has been exceeded",
                self.status_bool_key: False,
                self.status_code_key: -444
            }))
        if model_name_key in data and data[model_name_key]:
            interface = interface_manager.get_by_name(model_name)
        else:
            interface = interface_manager.get_by_size(size_string)
        if not interface:
            logger.info('Service is not ready!')
            return self.finish(json_encode(
                {self.message_key: "", self.status_bool_key: False, self.status_code_key: 999}
            ))

        output_split = output_split if 'output_split' in data else interface.model_conf.output_split

        if need_color:
            bytes_batch = [color_extract.separate_color(_, color_map[need_color]) for _ in bytes_batch]
        if interface.model_conf.corp_params:
            bytes_batch = corp_to_multi.parse_multi_img(bytes_batch, interface.model_conf.corp_params)
        if interface.model_conf.exec_map and not param_key:
            logger.info('[{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, size_string, request_count, log_params,
                "The model is missing the param_key parameter because the model is configured with ExecuteMap.",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(
                {
                    self.message_key: "Missing the parameter [param_key].",
                    self.status_bool_key: False,
                    self.status_code_key: 474
                }
            ))

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch, param_key=param_key)
        if interface.model_conf.batch_model:
            auxiliary_index = list(interface.model_conf.batch_model.keys())[0]
            auxiliary_name = list(interface.model_conf.batch_model.values())[0]
            auxiliary_interface = interface_manager.get_by_name(auxiliary_name)
            auxiliary_image_batch, response = ImageUtils.get_image_batch(
                auxiliary_interface.model_conf,
                bytes_batch,
                param_key=param_key
            )
            auxiliary_result = yield self.predict(
                auxiliary_interface,
                auxiliary_image_batch[auxiliary_index: auxiliary_index+1],
                output_split,
                size_string,
                start_time
            )
            image_batch = np.delete(image_batch, auxiliary_index, axis=0).tolist()

        if not image_batch:
            logger.error('[{} {}] | [{}] - Size[{}] - Response[{}] - {} ms'.format(
                self.request.remote_ip, self.request.uri, interface.name, size_string, response,
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(response))

        response[self.message_key] = yield self.predict(
            interface, image_batch, output_split, size_string, start_time, log_params, request_count
        )

        if interface.model_conf.corp_params and interface.model_conf.output_coord:
            final_result = auxiliary_result + "," + response[self.message_key] if auxiliary_result else response[self.message_key]
            response[self.message_key] = corp_to_multi.get_coordinate(
                label=final_result,
                param_group=interface.model_conf.corp_params,
                title_index=[0]
            )
        return self.finish(json.dumps(response, ensure_ascii=False).replace("</", "<\\/"))


class AuthHandler(NoAuthHandler):

    @sign.signature_required
    def post(self):
        return super().post()


class SimpleHandler(BaseHandler):

    message_key: str = system_config.response_def_map['Message']
    status_bool_key = system_config.response_def_map['StatusBool']
    status_code_key = system_config.response_def_map['StatusCode']

    def post(self):
        start_time = time.time()

        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode(
                {self.message_key: "", self.status_bool_key: False, self.status_code_key: -999}
            ))

        bytes_batch, response = self.image_utils.get_bytes_batch(self.request.body)

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
            return self.finish(json_encode(
                {self.message_key: "", self.status_bool_key: False, self.status_code_key: 999}
            ))

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch, param_key=None)

        if not image_batch:
            logger.error('[{}] | [{}] - Size[{}] - Response[{}] - {} ms'.format(

                self.request.remote_ip, interface.name, size_string, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        result = interface.predict_batch(image_batch, None)
        logger.info('[{}] | [{}] - Size[{}] - Predict[{}] - {} ms'.format(
            self.request.remote_ip, interface.name, size_string, result, (time.time() - start_time) * 1000)
        )
        response[self.message_key] = result
        return self.write(json.dumps(response, ensure_ascii=False).replace("</", "<\\/"))


class ServiceHandler(BaseHandler):

    def get(self):
        response = {
            "total": interface_manager.total,
            "online": interface_manager.online_names,
            "invalid": interface_manager.invalid_group
        }
        return self.finish(json.dumps(response, ensure_ascii=False, indent=2))


class FileHandler(tornado.web.StaticFileHandler):
    def data_received(self, chunk):
        pass

    def set_extra_headers(self, path):
        self.set_header("Cache-control", "no-cache")


class HeartBeatHandler(BaseHandler):

    def get(self):
        self.finish("")


def make_app(route: list):
    return tornado.web.Application([
        (i['Route'], globals()[i['Class']], i.get("Param"))
        if "Param" in i else
        (i['Route'], globals()[i['Class']]) for i in route
    ])


if __name__ == "__main__":
    os.system("chcp 65001")
    parser = optparse.OptionParser()
    parser.add_option('-r', '--request_limit', type="int", default=-1, dest="request_limit")
    parser.add_option('-p', '--port', type="int", default=19952, dest="port")
    parser.add_option('-w', '--workers', type="int", default=50, dest="workers")
    opt, args = parser.parse_args()
    server_port = opt.port
    request_limit = opt.request_limit
    workers = opt.workers
    logger = system_config.logger
    tornado.log.enable_pretty_logging(logger=logger)
    interface_manager = InterfaceManager()
    threading.Thread(target=lambda: event_loop(system_config, model_path, interface_manager)).start()

    sign.set_auth([{'accessKey': system_config.access_key, 'secretKey': system_config.secret_key}])

    server_host = "0.0.0.0"
    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app(system_config.route_map)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.bind(server_port, server_host)
    http_server.start(1)
    # app.listen(server_port, server_host)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()

