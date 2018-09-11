#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
from flask import *
from flask_caching import Cache
from gevent import monkey
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from constants import RequestException
from exception import InvalidUsage
from interface import predict_b64
from signature import Signature

# The order cannot be changed, it must be before the flask.
monkey.patch_all()
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
sign = Signature()
_except = RequestException()


@cache.cached(timeout=30)
@app.before_request
def before_request():
    try:
        # Here you can add the relevant code to get the authentication information from the custom database.
        # The existing code is for reference only in terms of format.
        sign.set_auth([{'accessKey': "C180130204197838", 'secretKey': "62d7eb0d370e603acd651066236c878b"}])
    except Exception:
        # Here Exception needs to be changed to the corresponding exception you need.
        raise InvalidUsage(**_except.DATABASE_CONNECTION_ERROR)


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


@app.route('/captcha/auth/v2', methods=['POST'])
@sign.signature_required  # This decorator is required for certification.
def auth_request():
    """
    This api is used for captcha prediction with authentication
    :return:
    """
    if not request.json or 'image' not in request.json:
        abort(400)
    result, code, success = predict_b64(request.json['image'])
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
    result, code, success = predict_b64(request.json['image'])
    response = {
        'message': {'result': result},
        'code': code,
        'success': success
    }
    return json.dumps(response), 200


if __name__ == "__main__":
    server = WSGIServer(('0.0.0.0', 19951), app, handler_class=WebSocketHandler)
    server.serve_forever()
