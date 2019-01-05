#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

from PyInstaller.__main__ import run
""" Used to package as a single executable """

if __name__ == '__main__':

    # opts = ['flask_server.spec', '--distpath=dist']
    # run(opts)
    # opts = ['grpc_server.spec', '--distpath=dist']
    # run(opts)
    opts = ['tornado_server.spec', '--distpath=dist']
    run(opts)