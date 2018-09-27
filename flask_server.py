#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import grpc
import grpc_pb2
import grpc_pb2_grpc
import optparse
from logging import basicConfig, INFO
from flask import *
from flask_caching import Cache
from gevent import monkey
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from config import ModelConfig
from constants import RequestException
from exception import InvalidUsage
from interface import Interface
from signature import Signature, ServerType

# The order cannot be changed, it must be before the flask.
monkey.patch_all()
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
sign = Signature(ServerType.FLASK)
_except = RequestException()


@cache.cached(timeout=30)
@app.before_request
def before_request():
    try:
        # Here you can add the relevant code to get the authentication information from the custom database.
        # The existing code is for reference only in terms of format.
        sign.set_auth([{'accessKey': model.access_key, 'secretKey': model.secret_key}])
    except Exception:
        # Here Exception needs to be changed to the corresponding exception you need.
        raise InvalidUsage(**_except.UNKNOWN_SERVER_ERROR)


@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.errorhandler(400)
def server_error(error=None):
    message = "Bad Request"
    return jsonify(message=message, code=error.code, success=False)


@app.errorhandler(500)
def server_error(error=None):
    message = 'Internal Server Error'
    return jsonify(message=message, code=500, success=False)


@app.errorhandler(404)
def not_found(error=None):
    message = '404 Not Found'
    return jsonify(message=message, code=error.code, success=False)


@app.errorhandler(403)
def permission_denied(error=None):
    message = 'Forbidden'
    return jsonify(message=message, code=error.code, success=False)


def rpc_request(image):
    channel = grpc.insecure_channel('localhost:50054')
    stub = grpc_pb2_grpc.PredictStub(channel)
    response = stub.predict(grpc_pb2.PredictRequest(captcha_img=image))
    return response.result, response.code, response.success


@app.route('/captcha/auth/v2', methods=['POST'])
@sign.signature_required  # This decorator is required for certification.
def auth_request():
    """
    This api is used for captcha prediction with authentication
    :return:
    """
    if not request.json or 'image' not in request.json:
        abort(400)
    # # You can separate the http service and the gRPC service like this:
    # result, code, success = rpc_request(request.json['image'])
    result, code, success = interface.predict_b64(request.json['image'])
    response = {
        'message': {'result': result},
        'code': code,
        'success': success
    }
    return json.dumps(response), 200


@app.route('/captcha/v1', methods=['POST'])
def common_request():
    """
    This api is used for captcha prediction without authentication
    :return:
    """
    if not request.json or 'image' not in request.json:
        abort(400)
    # # You can separate the http service and the gRPC service like this:
    # result, code, success = rpc_request(request.json['image'])
    result, code, success = interface.predict_b64(request.json['image'])
    response = {
        'message': {'result': result},
        'code': code,
        'success': success
    }
    return json.dumps(response), 200


if __name__ == "__main__":
    basicConfig(level=INFO)

    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', type="int", default=19951, dest="port")
    parser.add_option('-m', '--config', type="str", default='model.yaml', dest="config")
    parser.add_option('-a', '--path', type="str", default='model', dest="model_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    model_conf = opt.config
    model_path = opt.model_path

    server_host = "0.0.0.0"
    model = ModelConfig(model_conf=model_conf, model_path=model_path)
    sign.set_auth([{'accessKey': model.access_key, 'secretKey': model.secret_key}])
    interface = Interface(model)

    print('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    server = WSGIServer((server_host, server_port), app, handler_class=WebSocketHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
