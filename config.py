#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import re
import uuid
import yaml
import hashlib
from character import *
from exception import exception, ConfigException


class Model(object):

    def __init__(self, model_conf='model.yaml', model_path='model'):
        self.model_path = model_path
        self.model_conf = model_conf
        self.model_conf_demo = 'model_demo.yaml'
        self.verify()

    def verify(self):
        if not os.path.exists(self.model_conf):
            exception(
                'Configuration File "{}" No Found. '
                'If it is used for the first time, please copy one from {} as {}'.format(
                    self.model_conf,
                    self.model_conf_demo,
                    self.model_path
                ), ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
            )

        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            exception(
                'For the first time, please put the trained model in the model directory.'
                , ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
            )

    @staticmethod
    def char_set(_type):
        if isinstance(_type, list):
            return _type
        if isinstance(_type, str):
            return SIMPLE_CHAR_SET.get(_type) if _type in SIMPLE_CHAR_SET.keys() else ConfigException.CHAR_SET_NOT_EXIST
        exception(
            "Character set configuration error, customized character set should be list type",
            ConfigException.CHAR_SET_INCORRECT
        )

    def __type(self, _object, _abbreviate=False):
        return re.findall(r"(?<=').*?(?=')", str(type(_object)))[0]

    def read_conf(self):
        with open(self.model_conf, 'r', encoding="utf-8") as sys_fp:
            sys_stream = sys_fp.read()
            return yaml.load(sys_stream)


class ModelConfig(Model):

    def __init__(self, model_conf='model.yaml', model_path='model', print_info=True):
        super().__init__(model_conf=model_conf, model_path=model_path)
        self.system = None
        self.device = None
        self.charset = None
        self.split_char = None
        self.gen_charset = None
        self.char_exclude = None
        self.charset_len = None
        self.target_model = None
        self.image_height = None
        self.image_width = None
        self.binaryzation = None
        self.smooth = None
        self.blur = None
        self.mac_address = None
        self.access_key = None
        self.secret_key = None
        self.use_default_authorization = None
        self.authorization = None
        self.compile_model_path = None
        self.model_name_md5 = None
        self.cf_model = self.read_conf()
        self.assignment()
        if print_info:
            self.print()

    def assignment(self):

        system = self.cf_model.get('System')
        self.device = system.get('Device') if system else None
        self.device = self.device if self.device else "cpu:0"

        self.charset = self.cf_model['Model'].get('CharSet')
        self.gen_charset = self.char_set(self.charset)
        if self.gen_charset == ConfigException.CHAR_SET_NOT_EXIST:
            exception(
                "The character set type does not exist, there is no character set named {}".format(self.charset),
                ConfigException.CHAR_SET_NOT_EXIST
            )

        self.char_exclude = self.cf_model['Model'].get('CharExclude')

        self.gen_charset = [i for i in self.char_set(self.charset) if i not in self.char_exclude]
        self.charset_len = len(self.gen_charset)

        self.target_model = self.cf_model['Model'].get('ModelName')

        self.split_char = self.cf_model['Model'].get('SplitChar')
        self.split_char = '' if not self.split_char else self.split_char

        self.binaryzation = self.cf_model['Pretreatment'].get('Binaryzation')
        self.smooth = self.cf_model['Pretreatment'].get('Smoothing')
        self.blur = self.cf_model['Pretreatment'].get('Blur')

        mac_address = hex(uuid.getnode())[2:]

        self.image_height = self.cf_model['Model'].get('ImageHeight')
        self.image_width = self.cf_model['Model'].get('ImageWidth')

        # ---AUTHORIZATION START---
        self.use_default_authorization = False
        self.authorization = self.cf_model.get('Security')
        if not self.authorization or not self.authorization.get('AccessKey') or not self.authorization.get('SecretKey'):
            self.use_default_authorization = True
            model_name_md5 = hashlib.md5(
                "{}".format(self.target_model).encode('utf8')).hexdigest()
            self.authorization = {
                'AccessKey': model_name_md5[0: 16],
                'SecretKey': hashlib.md5("{}{}".format(model_name_md5, mac_address).encode('utf8')).hexdigest()
            }

        self.access_key = self.authorization['AccessKey']
        self.secret_key = self.authorization['SecretKey']
        # ---AUTHORIZATION END---
        self.compile_model_path = os.path.join(self.model_path, '{}.pb'.format(self.target_model))
        if not os.path.exists(self.compile_model_path):
            exception(
                '{} not found, please put the trained model in the model directory.'.format(self.compile_model_path)
                , ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
            )

    def print(self):
        print('Loading Configuration...')
        print('--------------------------------------------------MODEL------------------------------------------------')
        print('MODEL_NAME:', self.target_model)
        print('COMPILE_MODEL_PATH:', self.compile_model_path)
        print('CHAR_SET_LEN: {}, CHAR_SET: {}'.format(self.charset_len, self.charset))
        print('------------------------------------------------SECURITY-----------------------------------------------')
        print('ACCESS_KEY: {}, SECRET_KEY: {}, USE_DEFAULT_CONFIG: {}'.format(
            self.access_key, self.secret_key, self.use_default_authorization))
        print('-------------------------------------------------------------------------------------------------------')

    def size_match(self, size_str):
        return size_str == self.size_string

    @property
    def size_string(self):
        return "{}x{}".format(self.image_width, self.image_height)
