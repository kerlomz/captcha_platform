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
from config import Config, blacklist, set_blacklist, whitelist, get_version
from utils import ImageUtils, ParamUtils, Arithmetic
from signature import Signature, ServerType
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from middleware import *
from event_loop import event_loop

tornado.options.define('ip_blacklist', default=list(), type=list)
tornado.options.define('ip_whitelist', default=list(), type=list)
tornado.options.define('ip_risk_times', default=dict(), type=dict)
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

    @property
    def request_incr(self):
        if self.request.remote_ip not in tornado.options.options.request_count:
            tornado.options.options.request_count[self.request.remote_ip] = 1
        else:
            tornado.options.options.request_count[self.request.remote_ip] += 1
        return tornado.options.options.request_count[self.request.remote_ip]

    def request_desc(self):
        if self.request.remote_ip not in tornado.options.options.request_count:
            return
        else:
            tornado.options.options.request_count[self.request.remote_ip] -= 1

    @property
    def global_request_incr(self):
        tornado.options.options.global_request_count += 1
        return tornado.options.options.global_request_count

    @staticmethod
    def global_request_desc():
        tornado.options.options.global_request_count -= 1

    @staticmethod
    def risk_ip_count(ip):
        if ip not in tornado.options.options.ip_risk_times:
            tornado.options.options.ip_risk_times[ip] = 1
        else:
            tornado.options.options.ip_risk_times[ip] += 1

    @staticmethod
    def risk_ip(ip):
        return tornado.options.options.ip_risk_times[ip]

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
    def predict(self, interface: Interface, image_batch, split_char):
        result = interface.predict_batch(image_batch, split_char)
        if interface.model_category == 'ARITHMETIC':
            if '=' in result or '+' in result or '-' in result or '×' in result or '÷' in result:
                result = result.replace("×", "*").replace("÷", "/")
                result = str(int(arithmetic.calc(result)))
        return result

    @staticmethod
    def match_blacklist(ip: str):
        for black_ip in tornado.options.options.ip_blacklist:
            if ip.startswith(black_ip):
                return True
        return False

    @staticmethod
    def match_whitelist(ip: str):
        for white_ip in tornado.options.options.ip_whitelist:
            if ip.startswith(white_ip):
                return True
        return False

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
            self.request_desc()
            self.global_request_desc()
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

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])
        if system_config.request_size_limit and size_string not in system_config.request_size_limit:
            self.request_desc()
            self.global_request_desc()
            logger.info('[{}] - [{} {}] | Size[{}] - [{}][{}] - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, size_string, global_count, log_params,
                "Image size is invalid.",
                round((time.time() - start_time) * 1000))
            )
            msg = system_config.request_size_limit.get("msg")
            msg = msg if msg else "The size of the picture is wrong. " \
                                  "Only the original image is supported. " \
                                  "Please do not take a screenshot!"
            return self.finish(json.dumps({
                self.uid_key: uid,
                self.message_key: msg,
                self.status_bool_key: False,
                self.status_code_key: -250
            }, ensure_ascii=False))

        if system_config.use_whitelist:
            assert_whitelist = self.match_whitelist(self.request.remote_ip)
            if not assert_whitelist:
                logger.info('[{}] - [{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                    uid, self.request.remote_ip, self.request.uri, size_string, request_count, log_params,
                    "Whitelist limit",
                    round((time.time() - start_time) * 1000))
                )
                return self.finish(json.dumps({
                    self.uid_key: uid,
                    self.message_key: "Only allow IP access in the whitelist",
                    self.status_bool_key: False,
                    self.status_code_key: -111
                }, ensure_ascii=False))

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

        assert_blacklist = self.match_blacklist(self.request.remote_ip)
        if assert_blacklist:
            logger.info('[{}] - [{} {}] | Size[{}]{}{} - Error[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, size_string, request_count, log_params,
                "The ip is on the risk blacklist (IP)",
                round((time.time() - start_time) * 1000))
            )
            return self.finish(json.dumps({
                self.uid_key: uid,
                self.message_key: system_config.exceeded_msg,
                self.status_bool_key: False,
                self.status_code_key: -110
            }, ensure_ascii=False))
        if request_limit != -1 and request_incr > request_limit:
            self.risk_ip_count(self.request.remote_ip)
            assert_blacklist_trigger = system_config.blacklist_trigger_times != -1
            if self.risk_ip(self.request.remote_ip) > system_config.blacklist_trigger_times and assert_blacklist_trigger:
                if self.request.remote_ip not in blacklist():
                    set_blacklist(self.request.remote_ip)
                    update_blacklist()
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
            self.request_desc()
            self.global_request_desc()
            logger.info('Service is not ready!')
            return self.finish(json_encode(
                {self.uid_key: uid, self.message_key: "", self.status_bool_key: False, self.status_code_key: 999}
            ))

        output_split = output_split if 'output_split' in data else interface.model_conf.output_split

        if interface.model_conf.corp_params:
            bytes_batch = corp_to_multi.parse_multi_img(bytes_batch, interface.model_conf.corp_params)

        exec_map = interface.model_conf.exec_map
        if exec_map and len(exec_map.keys()) > 1 and not param_key:
            self.request_desc()
            self.global_request_desc()
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
            self.request_desc()
            self.global_request_desc()
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

        if not image_batch:
            self.request_desc()
            self.global_request_desc()
            logger.error('[{}] - [{} {}] | [{}] - Size[{}] - Response[{}] - {} ms'.format(
                uid, self.request.remote_ip, self.request.uri, interface.name, size_string, response,
                round((time.time() - start_time) * 1000))
            )
            response[self.uid_key] = uid
            return self.finish(json_encode(response))

        predict_result = yield self.predict(interface, image_batch, output_split)

        if need_color:
            # only support six label and size [90x35].
            color_batch = np.resize(image_batch[0], (90, 35, 3))
            need_index = color_extract.predict_color(image_batch=[color_batch], color=color_map[need_color])
            predict_result = "".join([v for i, v in enumerate(predict_result) if i in need_index])

        uid_str = "[{}] - ".format(uid)
        logger.info('{}[{} {}] | [{}] - Size[{}]{}{} - Predict[{}] - {} ms'.format(
            uid_str, self.request.remote_ip, self.request.uri, interface.name, size_string, request_count, log_params,
            predict_result,
            round((time.time() - start_time) * 1000))
        )
        response[self.message_key] = predict_result
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
            "invalid": interface_manager.invalid_group,
            "blacklist": tornado.options.options.ip_blacklist
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


def update_blacklist():
    tornado.options.options.ip_blacklist = blacklist()


def make_app(route: list):
    return tornado.web.Application([
        (i['Route'], globals()[i['Class']], i.get("Param"))
        if "Param" in i else
        (i['Route'], globals()[i['Class']]) for i in route
    ])


trigger_specific = IntervalTrigger(seconds=system_config.request_count_interval)
trigger_global = IntervalTrigger(seconds=system_config.g_request_count_interval)
trigger_blacklist = IntervalTrigger(seconds=10)
scheduler.add_job(update_blacklist, trigger_blacklist)
scheduler.add_job(clear_specific_job, trigger_specific)
scheduler.add_job(clear_global_job, trigger_global)
scheduler.start()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        os.system("chcp 65001")
        os.system("title=Eve-DL Platform v0.1({})".format(get_version()))
    parser = optparse.OptionParser()

    request_limit = system_config.request_limit
    global_request_limit = system_config.global_request_limit

    parser.add_option('-p', '--port', type="int", default=system_config.default_port, dest="port")
    parser.add_option('-w', '--workers', type="int", default=50, dest="workers")
    opt, args = parser.parse_args()
    server_port = opt.port

    workers = opt.workers
    logger = system_config.logger
    # print('=============WITHOUT_LOGGER=============', system_config.without_logger)
    tornado.log.enable_pretty_logging(logger=logger)
    interface_manager = InterfaceManager()
    threading.Thread(target=lambda: event_loop(system_config, model_path, interface_manager)).start()

    sign.set_auth([{'accessKey': system_config.access_key, 'secretKey': system_config.secret_key}])

    tornado.options.options.ip_whitelist = whitelist()

    server_host = "0.0.0.0"
    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app = make_app(system_config.route_map)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.bind(server_port, server_host)
    http_server.start(1)
    tornado.ioloop.IOLoop.instance().start()



