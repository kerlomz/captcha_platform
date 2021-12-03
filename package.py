#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import cv2
import time
import stat
import socket
import paramiko
import platform
import distutils
import tensorflow as tf
tf.compat.v1.disable_v2_behavior()
from enum import Enum, unique
from utils import SystemUtils
from config import resource_path

from PyInstaller.__main__ import run, logger
""" Used to package as a single executable """

if platform.system() == 'Linux':
    if distutils.distutils_path.endswith('__init__.py'):
        distutils.distutils_path = os.path.dirname(distutils.distutils_path)

with open("./resource/VERSION", "w", encoding="utf8") as f:
    today = time.strftime("%Y%m%d", time.localtime(time.time()))
    f.write(today)


@unique
class Version(Enum):
    CPU = 'CPU'
    GPU = 'GPU'


if __name__ == '__main__':

    ver = Version.CPU

    upload = False
    server_ip = ""
    username = ""
    password = ""
    model_dir = "model"
    graph_dir = "graph"

    if ver == Version.GPU:
        opts = ['tornado_server_gpu.spec', '--distpath=dist']
    else:
        opts = ['tornado_server.spec', '--distpath=dist']
    run(opts)