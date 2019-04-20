#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import time
import optparse
import threading
from config import Config
from utils import ImageUtils
from interface import InterfaceManager
from watchdog.observers import Observer
from event_handler import FileEventHandler
from sanic import Sanic
from sanic.response import json
from signature import Signature, ServerType
from middleware import *

app = Sanic()
sign = Signature(ServerType.SANIC)


@app.route('/captcha/auth/v2', methods=['POST'])
@sign.signature_required  # This decorator is required for certification.
def auth_request(request):
    return common_request(request)


@app.route('/captcha/v1', methods=['POST'])
def no_auth_request(request):
    return common_request(request)


def common_request(request):
    """
    This api is used for captcha prediction without authentication
    :return:
    """
    start_time = time.time()
    if not request.json or 'image' not in request.json:
        print(request.json)
        return

    if interface_manager.total == 0:
        logger.info('There is currently no model deployment and services are not available.')
        return json({"message": "", "success": False, "code": -999})

    bytes_batch, response = ImageUtils.get_bytes_batch(request.json['image'])

    if not bytes_batch:
        logger.error('Type[{}] - Site[{}] - Response[{}] - {} ms'.format(
            request.json['model_type'], request.json['model_site'], response,
            (time.time() - start_time) * 1000)
        )
        return json(response)

    image_sample = bytes_batch[0]
    image_size = ImageUtils.size_of_image(image_sample)
    size_string = "{}x{}".format(image_size[0], image_size[1])

    if 'model_site' in request.json:
        interface = interface_manager.get_by_sites(request.json['model_site'], size_string, strict=system_config.strict_sites)
    elif 'model_type' in request.json:
        interface = interface_manager.get_by_type_size(size_string, request.json['model_type'])
    elif 'model_name' in request.json:
        interface = interface_manager.get_by_name(size_string, request.json['model_name'])
    else:
        interface = interface_manager.get_by_size(size_string)

    split_char = request.json['split_char'] if 'split_char' in request.json else interface.model_conf.split_char

    if 'need_color' in request.json and request.json['need_color']:
        bytes_batch = [color_extract.separate_color(_, color_map[request.json['need_color']]) for _ in bytes_batch]

    image_batch, response = ImageUtils.get_image_batch(interface.model_conf, bytes_batch)

    if not image_batch:
        logger.error('[{}] - Size[{}] - Type[{}] - Site[{}] - Response[{}] - {} ms'.format(
            interface.name, size_string, request.json['model_type'], request.json['model_site'], response,
            (time.time() - start_time) * 1000)
        )
        return json(response)

    result = interface.predict_batch(image_batch, split_char)
    logger.info('[{}] - Size[{}] - Type[{}] - Site[{}] - Predict Result[{}] - {} ms'.format(
        interface.name,
        size_string,
        request.json.get('model_type'),
        request.json.get('model_site'),
        result,
        (time.time() - start_time) * 1000
    ))
    response['message'] = result
    return json(response)


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
    parser.add_option('-p', '--port', type="int", default=19953, dest="port")
    parser.add_option('-c', '--config', type="str", default='./config.yaml', dest="config")
    parser.add_option('-m', '--model_path', type="str", default='model', dest="model_path")
    parser.add_option('-g', '--graph_path', type="str", default='graph', dest="graph_path")
    opt, args = parser.parse_args()
    server_port = opt.port
    conf_path = opt.config
    model_path = opt.model_path
    graph_path = opt.graph_path

    system_config = Config(conf_path=conf_path, model_path=model_path, graph_path=graph_path)
    sign.set_auth([{'accessKey': system_config.access_key, 'secretKey': system_config.secret_key}])
    logger = system_config.logger
    interface_manager = InterfaceManager()
    threading.Thread(target=event_loop).start()

    server_host = "0.0.0.0"

    logger.info('Running on http://{}:{}/ <Press CTRL + C to quit>'.format(server_host, server_port))
    app.run(host=server_host, port=server_port)
