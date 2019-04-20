#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import time
import threading
from concurrent import futures

import grpc
import grpc_pb2
import grpc_pb2_grpc
import optparse
from utils import ImageUtils
from interface import InterfaceManager
from config import Config
from event_handler import FileEventHandler
from watchdog.observers import Observer
from middleware import *

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Predict(grpc_pb2_grpc.PredictServicer):

    def predict(self, request, context):
        start_time = time.time()
        bytes_batch, status = ImageUtils.get_bytes_batch(request.image)

        if interface_manager.total == 0:
            logger.info('There is currently no model deployment and services are not available.')
            return {"result": "", "success": False, "code": -999}

        if not bytes_batch:
            return grpc_pb2.PredictResult(result="", success=status['success'], code=status['code'])

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        size_string = "{}x{}".format(image_size[0], image_size[1])
        if request.model_site:
            interface = interface_manager.get_by_sites(request.model_site, size_string, strict=system_config.strict_sites)
        elif request.model_name:
            interface = interface_manager.get_by_name(request.model_name)
        elif request.model_type:
            interface = interface_manager.get_by_type_size(size_string, request.model_type)
        else:
            interface = interface_manager.get_by_size(size_string)
        if not interface:
            logger.info('Service is not ready!')
            return {"result": "", "success": False, "code": 999}

        if request.need_color:
            bytes_batch = [color_extract.separate_color(_, color_map[request.need_color]) for _ in bytes_batch]

        image_batch, status = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            return grpc_pb2.PredictResult(result="", success=status['success'], code=status['code'])

        result = interface.predict_batch(image_batch, request.split_char)
        logger.info('[{}] - Size[{}] - Type[{}] - Site[{}] - Predict Result[{}] - {} ms'.format(
            interface.name,
            size_string,
            request.model_type,
            request.model_site,
            result,
            (time.time() - start_time) * 1000
        ))
        return grpc_pb2.PredictResult(result=result, success=status['success'], code=status['code'])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    grpc_pb2_grpc.add_PredictServicer_to_server(Predict(), server)
    server.add_insecure_port('[::]:50054')
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


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


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=50054, dest="port")
    parser.add_option('-c', '--config', type="str", default='./config.yaml', dest="config")
    parser.add_option('-m', '--model_path', type="str", default='model', dest="model_path")
    parser.add_option('-g', '--graph_path', type="str", default='graph', dest="graph_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    conf_path = opt.config
    model_path = opt.model_path
    graph_path = opt.graph_path
    system_config = Config(conf_path=conf_path, model_path=model_path, graph_path=graph_path)
    interface_manager = InterfaceManager()
    threading.Thread(target=event_loop).start()

    logger = system_config.logger
    server_host = "0.0.0.0"

    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    serve()
