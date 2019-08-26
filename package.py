#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import stat
import socket
import paramiko
import distutils
from utils import SystemUtils

from PyInstaller.__main__ import run, logger
""" Used to package as a single executable """
if distutils.distutils_path.endswith('__init__.py'):
    distutils.distutils_path = os.path.dirname(distutils.distutils_path)


if __name__ == '__main__':

    server_ip = ""
    username = ""
    password = ""
    model_dir = "model"
    graph_dir = "graph"
    # opts = ['flask_server.spec', '--distpath=dist']
    # run(opts)
    # opts = ['grpc_server.spec', '--distpath=dist']
    # run(opts)
    opts = ['tornado_server.spec', '--distpath=dist']
    run(opts)

    transport = paramiko.Transport(sock=(server_ip, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    with open("dist/start.sh", "w", encoding="utf8") as f:
        f.write("nohup ./captcha_platform_tornado &")

    SystemUtils.empty(sftp, '/home/captcha_platform')
    logger.info('uploading app...')

    SystemUtils.empty(sftp, '/home/captcha_platform/graph')
    SystemUtils.empty(sftp, '/home/captcha_platform/model')

    for model in os.listdir(model_dir):
        if os.path.isdir(model):
            continue
        sftp.put(os.path.join(model_dir, model), '/home/captcha_platform/model/{}'.format(model))

    for graph in os.listdir(graph_dir):
        sftp.put(os.path.join(graph_dir, graph), '/home/captcha_platform/graph/{}'.format(graph))

    sftp.put("dist/captcha_platform_tornado", '/home/captcha_platform/captcha_platform_tornado')
    sftp.put("dist/start.sh", '/home/captcha_platform/start.sh')
    sftp.put("config.yaml", '/home/captcha_platform/config.yaml')

    sftp.chmod('/home/captcha_platform/captcha_platform_tornado', stat.S_IRWXU)
    sftp.chmod('/home/captcha_platform/start.sh', stat.S_IRWXU)

    logger.info('uploaded.')
    logger.info('update completed!')
    transport.close()