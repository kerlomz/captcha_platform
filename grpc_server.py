#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import time
from concurrent import futures

import grpc
import grpc_pb2
import grpc_pb2_grpc
import optparse
from interface import Interface, InterfaceManager
from config import ModelConfig
from utils import ImageUtils
from graph_session import GraphSessionPool, GraphSession

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Predict(grpc_pb2_grpc.PredictServicer):

    def predict(self, request, context):

        bytes_batch, status = ImageUtils.get_bytes_batch(request.captcha_img)
        if not bytes_batch:
            grpc_pb2.PredictResult(result="", success=status['success'], code=status['code'])

        image_sample = bytes_batch[0]
        image_size = ImageUtils.size_of_image(image_sample)
        interface = interface_manager.get_by_size("{}x{}".format(image_size[1], image_size[0]))
        image_batch, status = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

        if not image_batch:
            return grpc_pb2.PredictResult(result="", success=status['success'], code=status['code'])

        result = interface.predict_batch(image_batch, request.split_char)
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


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=50054, dest="port")
    parser.add_option('-m', '--config', type="str", default='model.yaml', dest="config")
    parser.add_option('-a', '--path', type="str", default='model', dest="model_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    model_conf = opt.config
    model_path = opt.model_path

    server_host = "0.0.0.0"
    default_model = ModelConfig(model_conf=model_conf, model_path=model_path)
    default_session = GraphSession(default_model)
    session_pool = GraphSessionPool(default_session)
    default_interface = Interface(default_model, session_pool)
    interface_manager = InterfaceManager(default_interface)

    print('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    serve()
