#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import uuid
import yaml
import hashlib
import logging
from logging.handlers import TimedRotatingFileHandler
from category import *
from constants import SystemConfig, ModelField, ModelScene

MODEL_SCENE_MAP = {
    'Classification': ModelScene.Classification
}

MODEL_FIELD_MAP = {
    'Image': ModelField.Image,
    'Text': ModelField.Text
}


class Config(object):
    def __init__(self, conf_path: str, graph_path: str = None, model_path: str = None):
        self.model_path = model_path
        self.conf_path = conf_path
        self.graph_path = graph_path
        self.sys_cf = self.read_conf
        self.access_key = None
        self.secret_key = None
        self.default_model = self.sys_cf['System']['DefaultModel']
        self.split_flag = self.sys_cf['System']['SplitFlag']
        self.split_flag = self.split_flag if isinstance(self.split_flag, bytes) else SystemConfig.split_flag

        self.route_map = self.sys_cf.get('RouteMap')
        self.route_map = self.route_map if self.route_map else SystemConfig.default_route
        self.log_path = "logs"
        self.request_def_map = self.sys_cf.get('RequestDef')
        self.request_def_map = self.request_def_map if self.request_def_map else SystemConfig.default_config['RequestDef']
        self.response_def_map = self.sys_cf.get('ResponseDef')
        self.response_def_map = self.response_def_map if self.response_def_map else SystemConfig.default_config['ResponseDef']
        self.save_path = self.sys_cf['System'].get("SavePath")
        self.request_count_interval = self.sys_cf['System'].get("RequestCountInterval")
        self.request_limit = self.sys_cf['System'].get("RequestLimit")
        self.request_limit = self.request_limit if self.request_limit else -1
        self.request_count_interval = self.request_count_interval if self.request_count_interval else 60 * 60 * 24
        self.logger_tag = self.sys_cf['System'].get('LoggerTag')
        self.logger_tag = self.logger_tag if self.logger_tag else "coriander"
        self.logger = logging.getLogger(self.logger_tag)
        self.use_default_authorization = False
        self.authorization = None
        self.init_logger()
        self.assignment()

    def init_logger(self):
        self.logger.setLevel(logging.INFO)

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
        if not os.path.exists(self.graph_path):
            os.makedirs(self.graph_path)

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
        if not os.path.exists(self.conf_path):
            with open(self.conf_path, 'w', encoding="utf-8") as sys_fp:
                sys_fp.write(yaml.safe_dump(SystemConfig.default_config))
                return SystemConfig.default_config
        with open(self.conf_path, 'r', encoding="utf-8") as sys_fp:
            sys_stream = sys_fp.read()
            return yaml.load(sys_stream, Loader=yaml.SafeLoader)


class Model(object):

    def __init__(self, conf: Config, model_conf_path: str):
        self.conf = conf
        self.logger = self.conf.logger
        self.graph_path = conf.graph_path
        self.model_path = conf.model_path
        self.model_conf_path = model_conf_path
        self.model_conf_demo = 'model_demo.yaml'
        self.verify()

    def verify(self):
        if not os.path.exists(self.model_conf_path):
            raise Exception(
                'Configuration File "{}" No Found. '
                'If it is used for the first time, please copy one from {} as {}'.format(
                    self.model_conf_path,
                    self.model_conf_demo,
                    self.model_path
                )
            )

        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            raise Exception(
                'For the first time, please put the trained model in the model directory.'
            )

    def category_extract(self, param):
        if isinstance(param, list):
            return param
        if isinstance(param, str):
            if param in SIMPLE_CATEGORY_MODEL.keys():
                return SIMPLE_CATEGORY_MODEL.get(param)
            self.logger.error(
                "Category set configuration error, customized category set should be list type"
            )
            return None

    @property
    def model_conf(self) -> dict:
        with open(self.model_conf_path, 'r', encoding="utf-8") as sys_fp:
            sys_stream = sys_fp.read()
            return yaml.load(sys_stream, Loader=yaml.SafeLoader)


class ModelConfig(Model):

    model_exists: bool = False

    def __init__(self, conf: Config, model_conf_path: str):
        super().__init__(conf=conf, model_conf_path=model_conf_path)

        self.conf = conf

        """MODEL"""
        self.model_root: dict = self.model_conf['Model']
        self.model_name: str = self.model_root.get('ModelName')
        self.model_version: float = self.model_root.get('Version')
        self.model_version = self.model_version if self.model_version else 1.0
        self.model_field_param: str = self.model_root.get('ModelField')
        self.model_field: ModelField = ModelConfig.param_convert(
            source=self.model_field_param,
            param_map=MODEL_FIELD_MAP,
            text="Current model field ({model_field}) is not supported".format(model_field=self.model_field_param),
            code=50002
        )

        self.model_scene_param: str = self.model_root.get('ModelScene')

        self.model_scene: ModelScene = ModelConfig.param_convert(
            source=self.model_scene_param,
            param_map=MODEL_SCENE_MAP,
            text="Current model scene ({model_scene}) is not supported".format(model_scene=self.model_scene_param),
            code=50001
        )

        """SYSTEM"""
        self.checkpoint_tag = 'checkpoint'
        self.system_root: dict = self.model_conf['System']
        self.memory_usage: float = self.system_root.get('MemoryUsage')

        """FIELD PARAM - IMAGE"""
        self.field_root: dict = self.model_conf['FieldParam']
        self.category_param = self.field_root.get('Category')
        self.category_value = self.category_extract(self.category_param)
        if self.category_value is None:
            raise Exception(
                "The category set type does not exist, there is no category set named {}".format(self.category_param),
            )
        self.category: list = SPACE_TOKEN + self.category_value
        self.category_num: int = len(self.category)
        self.image_channel: int = self.field_root.get('ImageChannel')
        self.image_width: int = self.field_root.get('ImageWidth')
        self.image_height: int = self.field_root.get('ImageHeight')
        self.resize: list = self.field_root.get('Resize')
        self.output_split = self.field_root.get('OutputSplit')
        self.output_split = self.output_split if self.output_split else ""
        self.corp_params = self.field_root.get('CorpParams')
        self.output_coord = self.field_root.get('OutputCoord')
        self.batch_model = self.field_root.get('BatchModel')
        self.external_model = self.field_root.get('ExternalModelForCorp')
        self.category_split = self.field_root.get('CategorySplit')

        """PRETREATMENT"""
        self.pretreatment_root = self.model_conf.get('Pretreatment')
        self.pre_binaryzation = self.get_var(self.pretreatment_root, 'Binaryzation', -1)
        self.pre_replace_transparent = self.get_var(self.pretreatment_root, 'ReplaceTransparent', True)
        self.pre_horizontal_stitching = self.get_var(self.pretreatment_root, 'HorizontalStitching', False)
        self.pre_concat_frames = self.get_var(self.pretreatment_root, 'ConcatFrames', -1)
        self.pre_blend_frames = self.get_var(self.pretreatment_root, 'BlendFrames', -1)
        self.exec_map = self.get_var(self.pretreatment_root, 'ExecuteMap', None)

        """COMPILE_MODEL"""
        self.compile_model_path = os.path.join(self.graph_path, '{}.pb'.format(self.model_name))
        if not os.path.exists(self.compile_model_path):
            if not os.path.exists(self.graph_path):
                os.makedirs(self.graph_path)
            self.logger.error(
                '{} not found, please put the trained model in the graph directory.'.format(self.compile_model_path)
            )
        else:
            self.model_exists = True

    @staticmethod
    def param_convert(source, param_map: dict, text, code, default=None):
        if source is None:
            return default
        if source not in param_map.keys():
            raise Exception(text)
        return param_map[source]

    def size_match(self, size_str):
        return size_str == self.size_string

    @staticmethod
    def get_var(src: dict, name: str, default=None):
        if not src:
            return default
        return src.get(name)

    @property
    def size_string(self):
        return "{}x{}".format(self.image_width, self.image_height)
