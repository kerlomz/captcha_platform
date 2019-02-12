#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import uuid
import yaml
import hashlib
import logging
from logging.handlers import TimedRotatingFileHandler
from character import *


class Config(object):
    def __init__(self, conf_path: str, graph_path: str = None, model_path: str = None):
        self.model_path = model_path
        self.conf_path = conf_path
        self.graph_path = graph_path
        self.sys_cf = self.read_conf
        self.access_key = None
        self.secret_key = None
        self.default_model = self.sys_cf['System']['DefaultModel']
        self.split_flag = eval(self.sys_cf['System']['SplitFlag'])
        self.strict_sites = self.sys_cf['System'].get('StrictSites')
        self.strict_sites = True if self.strict_sites is None else self.strict_sites
        self.log_path = "logs"
        self.logger_tag = self.sys_cf['System'].get('LoggerTag')
        self.logger_tag = self.logger_tag if self.logger_tag else "coriander"
        self.logger = logging.getLogger(self.logger_tag)
        self.static_path = self.sys_cf['System'].get('StaticPath')
        self.static_path = self.static_path if self.static_path else 'static'
        self.use_default_authorization = False
        self.authorization = None
        self.init_logger()
        self.assignment()

    def init_logger(self):
        self.logger.setLevel(logging.INFO)
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)
        file_handler = TimedRotatingFileHandler(
            '{}/{}.log'.format(self.log_path, "captcha_platform"),
            when="MIDNIGHT",
            interval=1,
            backupCount=180,
            encoding='utf-8'
        )
        self.logger.propagate = False
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def assignment(self):
        # ---AUTHORIZATION START---
        mac_address = hex(uuid.getnode())[2:]
        self.use_default_authorization = False
        self.authorization = self.sys_cf.get('Security')
        if not self.authorization or not self.authorization.get('AccessKey') or not self.authorization.get('SecretKey'):
            self.use_default_authorization = True
            model_name_md5 = hashlib.md5(
                "{}".format(self.default_model).encode('utf8')).hexdigest()
            self.authorization = {
                'AccessKey': model_name_md5[0: 16],
                'SecretKey': hashlib.md5("{}{}".format(model_name_md5, mac_address).encode('utf8')).hexdigest()
            }
        self.access_key = self.authorization['AccessKey']
        self.secret_key = self.authorization['SecretKey']
        # ---AUTHORIZATION END---

    @property
    def read_conf(self):
        with open(self.conf_path, 'r', encoding="utf-8") as sys_fp:
            sys_stream = sys_fp.read()
            return yaml.load(sys_stream)


class Model(object):

    def __init__(self, conf: Config, model_conf: str):
        self.conf = conf
        self.logger = self.conf.logger
        self.graph_path = conf.graph_path
        self.model_path = conf.model_path
        self.model_conf = model_conf
        self.model_conf_demo = 'model_demo.yaml'
        self.verify()

    def verify(self):
        if not os.path.exists(self.model_conf):
            raise Exception(
                'Configuration File "{}" No Found. '
                'If it is used for the first time, please copy one from {} as {}'.format(
                    self.model_conf,
                    self.model_conf_demo,
                    self.model_path
                )
            )

        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            raise Exception(
                'For the first time, please put the trained model in the model directory.'
            )

    def char_set(self, _type):
        if isinstance(_type, list):
            return _type
        if isinstance(_type, str):
            return SIMPLE_CHAR_SET.get(_type) if _type in SIMPLE_CHAR_SET.keys() else None
        self.logger.error(
            "Character set configuration error, customized character set should be list type"
        )

    @property
    def read_conf(self):
        with open(self.model_conf, 'r', encoding="utf-8") as sys_fp:
            sys_stream = sys_fp.read()
            return yaml.load(sys_stream)


class ModelConfig(Model):

    def __init__(self, conf: Config, model_conf: str):
        super().__init__(conf=conf, model_conf=model_conf)
        self.system = None
        self.device = None
        self.device_usage = None
        self.charset = None
        self.split_char = None
        self.gen_charset = None
        self.char_exclude = None
        self.charset_len = None
        self.target_model = None
        self.model_type = None
        self.image_height = None
        self.image_width = None
        self.resize = None
        self.binaryzation = None
        self.smooth = None
        self.blur = None
        self.replace_transparent = None
        self.model_site = None
        self.version = None
        self.mac_address = None
        self.compile_model_path = None
        self.model_name_md5 = None
        self.color_engine = None
        self.cf_model = self.read_conf
        self.model_exists = False
        self.assignment()
        self.graph_name = "{}&{}".format(self.target_model, self.size_string)

    def assignment(self):

        system = self.cf_model.get('System')
        self.device = system.get('Device') if system else None
        self.device = self.device if self.device else "cpu:0"
        self.device_usage = system.get('DeviceUsage') if system else None
        self.device_usage = self.device_usage if self.device_usage else 0.1

        self.charset = self.cf_model['Model'].get('CharSet')
        self.gen_charset = self.char_set(self.charset)
        if self.gen_charset is None:
            raise Exception(
                "The character set type does not exist, there is no character set named {}".format(self.charset),
            )

        self.char_exclude = self.cf_model['Model'].get('CharExclude')

        self.gen_charset = [''] + [i for i in self.char_set(self.charset) if i not in self.char_exclude]
        self.charset_len = len(self.gen_charset)

        self.target_model = self.cf_model['Model'].get('ModelName')
        self.model_type = self.cf_model['Model'].get('ModelType')
        self.model_site = self.cf_model['Model'].get('Sites')
        self.model_site = self.model_site if self.model_site else []
        self.version = self.cf_model['Model'].get('Version')
        self.version = self.version if self.version else 1.0
        self.split_char = self.cf_model['Model'].get('SplitChar')
        self.split_char = '' if not self.split_char else self.split_char

        self.image_height = self.cf_model['Model'].get('ImageHeight')
        self.image_width = self.cf_model['Model'].get('ImageWidth')
        self.color_engine = self.cf_model['Model'].get('ColorEngine')
        self.color_engine = self.color_engine if self.color_engine else 'opencv'

        self.binaryzation = self.cf_model['Pretreatment'].get('Binaryzation')
        self.smooth = self.cf_model['Pretreatment'].get('Smoothing')
        self.blur = self.cf_model['Pretreatment'].get('Blur')
        self.blur = self.cf_model['Pretreatment'].get('Blur')
        self.resize = self.cf_model['Pretreatment'].get('Resize')
        self.resize = self.resize if self.resize else [self.image_width, self.image_height]
        self.replace_transparent = self.cf_model['Pretreatment'].get('ReplaceTransparent')
        self.compile_model_path = os.path.join(self.graph_path, '{}.pb'.format(self.target_model))
        if not os.path.exists(self.compile_model_path):
            if not os.path.exists(self.graph_path):
                os.makedirs(self.graph_path)
            self.logger.error(
                '{} not found, please put the trained model in the graph directory.'.format(self.compile_model_path)
            )
        else:
            self.model_exists = True

    def size_match(self, size_str):
        return size_str == self.size_string

    @property
    def size_string(self):
        return "{}x{}".format(self.image_width, self.image_height)
