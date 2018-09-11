#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import time
from concurrent import futures

import grpc

import grpc_pb2
import grpc_pb2_grpc
from interface import predict_b64

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Predict(grpc_pb2_grpc.PredictServicer):

    def predict(self, request, context):
        result, code, success = predict_b64(request.captcha_img)
        return grpc_pb2.PredictResult(result=result, success=success)


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
    serve()
