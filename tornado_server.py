#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import uuid
import time
import json
import platform
import numpy as np
import asyncio
import hashlib
import optparse
import threading
import tornado.ioloop
import tornado.log
import tornado.gen
import tornado.httpserver
import tornado.options
from pytz import utc
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.background import BackgroundScheduler
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
tornado.options.define('global_request_count', default=0, type=int)
model_path = "model"
system_config = Config(conf_path="config.yaml", model_path=model_path, graph_path="graph")
sign = Signature(ServerType.TORNADO, system_config)
arithmetic = Arithmetic()
semaphore = asyncio.Semaphore(500)

scheduler = BackgroundScheduler(timezone=utc)


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
            500: dict(StatusCode=code, Message="Internal Server Error", StatusBool=False),
            400: dict(StatusCode=code, Message="Bad Request", StatusBool=False),
            404: dict(StatusCode=code, Message="404 Not Found", StatusBool=False),
            403: dict(StatusCode=code, Message="Forbidden", StatusBool=False),
            405: dict(StatusCode=code, Message="Method Not Allowed", StatusBool=False),
        }
        if code in system.keys():
            code_dict = Response.parse(system.get(code), system_config.response_def_map)
        else:
            code_dict = self.exception.find(code)
        return self.finish(json_encode(code_dict))


class NoAuthHandler(BaseHandler):

    uid_key: str = system_config.response_def_map['Uid']
    message_key: str = system_config.response_def_map['Message']
    status_bool_key = system_config.response_def_map['StatusBool']
    status_code_key = system_config.response_def_map['StatusCode']

    @staticmethod
    def save_image(uid, label, image_bytes):
        if system_config.save_path:
            if not os.path.exists(system_config.save_path):
                os.makedirs(system_config.save_path)
            save_name = "{}_{}.png".format(label, uid)
            with open(os.path.join(system_config.save_path, save_name), "wb") as f:
                f.write(image_bytes)

    @run_on_executor
    def predict(self, interface: Interface, image_batch, split_char, size_string, start_time, log_params, request_count, uid=""):
        result = interface.predict_batch(image_batch, split_char)
        if interface.model_category == 'ARITHMETIC':
            if '=' in result or '+' in result or '-' in result or '×' in result or '÷' in result:
                result = result.replace("×", "*").replace("÷", "/")
                result = str(int(arithmetic.calc(result)))
        uid_str = "[{}] - ".format(uid)
        logger.info('{}[{} {}] | [{}] - Size[{}]{}{} - Predict[{}] - {} ms'.format(
            uid_str, self.request.remote_ip, self.request.uri, interface.name, size_string, request_count, log_params, result,
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

    @property
    def global_request_incr(self):
        tornado.options.options.global_request_count += 1
        return tornado.options.options.global_request_count

    @tornado.gen.coroutine
    def post(self):
        uid = str(uuid.uuid1())
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
        global_count = self.global_request_incr
        request_count = " - Count[{}]".format(request_incr)
        log_params = " - ParamKey[{}]".format(param_key) if param_key else ""
        log_params += " - NeedColor[{}]".format(need_color) if need_color else ""

        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode(
                {self.uid_key: uid, self.message_key: "", self.status_bool_key: False, self.status_code_key: -999}
            ))
        bytes_batch, response = self.image_utils.get_bytes_batch(data[input_data_key])

        if not bytes_batch:
            logger.error('[{}] - [{} {}] | - Response[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        # auxiliary_result = None

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])
        if global_request_limit != -1 and global_count > global_request_limit:
            logger.info('[{}] - [{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, size_string, global_count, log_params,
                "Maximum number of requests exceeded (G)",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json.dumps({
                self.uid_key: uid,
                self.message_key: system_config.exceeded_msg,
                self.status_bool_key: False,
                self.status_code_key: -555
            }, ensure_ascii=False))

        if request_limit != -1 and request_incr > request_limit:
            logger.info('[{}] - [{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, size_string, request_count, log_params,
                "Maximum number of requests exceeded (IP)",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json.dumps({
                self.uid_key: uid,
                self.message_key: system_config.exceeded_msg,
                self.status_bool_key: False,
                self.status_code_key: -444
            }, ensure_ascii=False))
        if model_name_key in data and data[model_name_key]:
            interface = interface_manager.get_by_name(model_name)
        else:
            interface = interface_manager.get_by_size(size_string)
        if not interface:
            logger.info('Service is not ready!')
            return self.finish(json_encode(
                {self.uid_key: uid, self.message_key: "", self.status_bool_key: False, self.status_code_key: 999}
            ))

        output_split = output_split if 'output_split' in data else interface.model_conf.output_split

        if need_color:
            bytes_batch = [color_extract.separate_color(_, color_map[need_color]) for _ in bytes_batch]

        if interface.model_conf.corp_params:
            bytes_batch = corp_to_multi.parse_multi_img(bytes_batch, interface.model_conf.corp_params)

        exec_map = interface.model_conf.exec_map
        if exec_map and len(exec_map.keys()) > 1 and not param_key:
            logger.info('[{}] - [{} {}] | [{}] - Size[{}]{}{} - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, interface.name, size_string, request_count, log_params,
                "The model is missing the param_key parameter because the model is configured with ExecuteMap.",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(
                {
                    self.uid_key: uid,
                    self.message_key: "Missing the parameter [param_key].",
                    self.status_bool_key: False,
                    self.status_code_key: 474
                }
            ))
        elif exec_map and param_key and param_key not in exec_map:
            logger.info('[{}] - [{} {}] | [{}] - Size[{}]{}{} - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, interface.name, size_string, request_count, log_params,
                "The param_key parameter is not support in the model.",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(
                {
                    self.uid_key: uid,
                    self.message_key: "Not support the parameter [param_key].",
                    self.status_bool_key: False,
                    self.status_code_key: 474
                }
            ))
        elif exec_map and len(exec_map.keys()) == 1:
            param_key = list(interface.model_conf.exec_map.keys())[0]

        if interface.model_conf.external_model and interface.model_conf.corp_params:
            result = []
            len_of_result = []
            pre_corp_num = 0
            for corp_param in interface.model_conf.corp_params:
                corp_size = corp_param['corp_size']
                corp_num_list = corp_param['corp_num']
                corp_num = corp_num_list[0] * corp_num_list[1]
                sub_bytes_batch = bytes_batch[pre_corp_num: pre_corp_num + corp_num]
                pre_corp_num = corp_num
                size_string = "{}x{}".format(corp_size[0], corp_size[1])

                sub_interface = interface_manager.get_by_size(size_string)

                image_batch, response = ImageUtils.get_image_batch(
                    sub_interface.model_conf, sub_bytes_batch, param_key=param_key
                )

                text = yield self.predict(
                    sub_interface, image_batch, output_split, size_string, start_time, log_params, request_count, uid=uid
                )
                result.append(text)
                len_of_result.append(len(result[0].split(sub_interface.model_conf.category_split)))

            response[self.message_key] = interface.model_conf.output_split.join(result)
            if interface.model_conf.corp_params and interface.model_conf.output_coord:
                # final_result = auxiliary_result + "," + response[self.message_key]
                # if auxiliary_result else response[self.message_key]
                final_result = response[self.message_key]
                response[self.message_key] = corp_to_multi.get_coordinate(
                    label=final_result,
                    param_group=interface.model_conf.corp_params,
                    title_index=[i for i in range(len_of_result[0])]
                )
            return self.finish(json.dumps(response, ensure_ascii=False).replace("</", "<\\/"))
        else:
            image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch, param_key=param_key)

        # if interface.model_conf.batch_model:
        #     auxiliary_index = list(interface.model_conf.batch_model.keys())[0]
        #     auxiliary_name = list(interface.model_conf.batch_model.values())[0]
        #     auxiliary_interface = interface_manager.get_by_name(auxiliary_name)
        #     auxiliary_image_batch, response = ImageUtils.get_image_batch(
        #         auxiliary_interface.model_conf,
        #         bytes_batch,
        #         param_key=param_key
        #     )
        #     auxiliary_result = yield self.predict(
        #         auxiliary_interface,
        #         auxiliary_image_batch[auxiliary_index: auxiliary_index+1],
        #         output_split,
        #         size_string,
        #         start_time
        #     )
        #     image_batch = np.delete(image_batch, auxiliary_index, axis=0).tolist()

        if not image_batch:
            logger.error('[{}] - [{} {}] | [{}] - Size[{}] - Response[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, interface.name, size_string, response,
                round((time.time() - start_time) * 1000))
            )
            response[self.uid_key] = uid
            return self.finish(json_encode(response))

        response[self.message_key] = yield self.predict(
            interface, image_batch, output_split, size_string, start_time, log_params, request_count, uid=uid
        )
        response[self.uid_key] = uid
        self.executor.submit(self.save_image, uid, response[self.message_key], bytes_batch[0])
        # if interface.model_conf.corp_params and interface.model_conf.output_coord:
        #     # final_result = auxiliary_result + "," + response[self.message_key]
        #     # if auxiliary_result else response[self.message_key]
        #     final_result = response[self.message_key]
        #     response[self.message_key] = corp_to_multi.get_coordinate(
        #         label=final_result,
        #         param_group=interface.model_conf.corp_params,
        #         title_index=[0]
        #     )
        return self.finish(json.dumps(response, ensure_ascii=False).replace("</", "<\\/"))


class AuthHandler(NoAuthHandler):

    @sign.signature_required
    def post(self):
        return super().post()


class SimpleHandler(BaseHandler):

    uid_key: str = system_config.response_def_map['Uid']
    message_key: str = system_config.response_def_map['Message']
    status_bool_key = system_config.response_def_map['StatusBool']
    status_code_key = system_config.response_def_map['StatusCode']

    def post(self):
        uid = str(uuid.uuid1())
        param_key = None
        start_time = time.time()
        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return self.finish(json_encode(
                {self.uid_key: uid, self.message_key: "", self.status_bool_key: False, self.status_code_key: -999}
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

        exec_map = interface.model_conf.exec_map
        if exec_map and len(exec_map.keys()) > 1:
            logger.info('[{}] - [{} {}] | [{}] - Size[{}] - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, interface.name, size_string,
                "The model is configured with ExecuteMap, but the api do not support this param.",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json_encode(
                {
                    self.message_key: "the api do not support [ExecuteMap].",
                    self.status_bool_key: False,
                    self.status_code_key: 474
                }
            ))
        elif exec_map and len(exec_map.keys()) == 1:
            param_key = list(interface.model_conf.exec_map.keys())[0]

        image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch, param_key=param_key)

        if not image_batch:
            logger.error('[{}] - [{}] | [{}] - Size[{}] - Response[{}] - {} ms'.format(
                uid, self.request.remote_ip, interface.name, size_string, response,
                (time.time() - start_time) * 1000)
            )
            return self.finish(json_encode(response))

        result = interface.predict_batch(image_batch, None)
        logger.info('[{}] - [{}] | [{}] - Size[{}] - Predict[{}] - {} ms'.format(
            uid, self.request.remote_ip, interface.name, size_string, result, (time.time() - start_time) * 1000)
        )
        response[self.uid_key] = uid
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


def clear_specific_job():
    tornado.options.options.request_count = {}


def clear_global_job():
    tornado.options.options.global_request_count = 0


def make_app(route: list):
    return tornado.web.Application([
        (i['Route'], globals()[i['Class']], i.get("Param"))
        if "Param" in i else
        (i['Route'], globals()[i['Class']]) for i in route
    ])


trigger_specific = IntervalTrigger(seconds=system_config.request_count_interval)
trigger_global = IntervalTrigger(seconds=system_config.g_request_count_interval)
scheduler.add_job(clear_specific_job, trigger_specific)
scheduler.add_job(clear_global_job, trigger_global)
scheduler.start()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        os.system("chcp 65001")
    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=19952, dest="port")
    parser.add_option('-w', '--workers', type="int", default=50, dest="workers")
    opt, args = parser.parse_args()
    server_port = opt.port
    request_limit = system_config.request_limit
    global_request_limit = system_config.global_request_limit
    workers = opt.workers
    logger = system_config.logger
    print('=============WITHOUT_LOGGER=============', system_config.without_logger)
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

