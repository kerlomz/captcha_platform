#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import re
import sys

import yaml

from character import *
from exception import exception, ConfigException

MODEL_CONFIG_DEMO_PATH = 'model_demo.yaml'
MODEL_CONFIG_PATH = 'model.yaml'
MODEL_PATH = 'model'


if not os.path.exists(MODEL_CONFIG_PATH):
    exception(
        'Configuration File "{}" No Found. '
        'If it is used for the first time, please copy one from {} as {}'.format(
            MODEL_CONFIG_PATH,
            MODEL_CONFIG_DEMO_PATH,
            MODEL_CONFIG_PATH
        ), ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
    )

if not os.path.exists(MODEL_PATH):
    os.makedirs(MODEL_PATH)
    exception(
        'For the first time, please put the trained model in the model directory.'
        , ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
    )


with open(MODEL_CONFIG_PATH, 'r', encoding="utf-8") as sys_fp:
    sys_stream = sys_fp.read()
    cf_model = yaml.load(sys_stream)


def char_set(_type):
    if isinstance(_type, list):
        return _type
    if isinstance(_type, str):
        return SIMPLE_CHAR_SET.get(_type) if _type in SIMPLE_CHAR_SET.keys() else ConfigException.CHAR_SET_NOT_EXIST
    exception(
        "Character set configuration error, customized character set should be list type",
        ConfigException.CHAR_SET_INCORRECT
    )


def __type(_object, _abbreviate=False):
    return re.findall(r"(?<=').*?(?=')", str(type(_object)))[0]


SYSTEM = cf_model.get('System')
DEVICE = SYSTEM.get('Device') if SYSTEM else None
DEVICE = DEVICE if DEVICE else "cpu:0"

CHAR_SET = cf_model['Model'].get('CharSet')
GEN_CHAR_SET = char_set(CHAR_SET)
if GEN_CHAR_SET == ConfigException.CHAR_SET_NOT_EXIST:
    exception(
        "The character set type does not exist, there is no character set named {}".format(CHAR_SET),
        ConfigException.CHAR_SET_NOT_EXIST
    )

CHAR_EXCLUDE = cf_model['Model'].get('CharExclude')

GEN_CHAR_SET = [i for i in char_set(CHAR_SET) if i not in CHAR_EXCLUDE]
CHAR_SET_LEN = len(GEN_CHAR_SET)

TARGET_MODEL = cf_model['Model'].get('ModelName')

MAX_CAPTCHA_LEN = cf_model['Model'].get('CharLength')

IMAGE_CHANNEL = cf_model['Model'].get('ImageChannel')
MAGNIFICATION = cf_model['Pretreatment'].get('Magnification')
IMAGE_ORIGINAL_COLOR = cf_model['Pretreatment'].get('OriginalColor')
BINARYZATION = cf_model['Pretreatment'].get('Binaryzation')
SMOOTH = cf_model['Pretreatment'].get('Smoothing')
BLUR = cf_model['Pretreatment'].get('Blur')
INVERT = cf_model['Pretreatment'].get('Invert')
RESIZE = cf_model['Pretreatment'].get('Resize')
RESIZE = tuple(RESIZE) if RESIZE else None
MAGNIFICATION = None if RESIZE else MAGNIFICATION
MAGNIFICATION = MAGNIFICATION if MAGNIFICATION and MAGNIFICATION > 0 and isinstance(MAGNIFICATION, int) else 1

COMPILE_MODEL_PATH = os.path.join(MODEL_PATH, '{}.pb'.format(TARGET_MODEL))
if not os.path.exists(COMPILE_MODEL_PATH):
    exception(
        '{} not found, please put the trained model in the model directory.'.format(COMPILE_MODEL_PATH)
        , ConfigException.MODEL_CONFIG_PATH_NOT_EXIST
    )


print('COMPILE_MODEL_PATH:', COMPILE_MODEL_PATH)
print('Loading Configuration...')
print('---------------------------------------------------------------------------------')
# print("PROJECT_PARENT_PATH", PROJECT_PARENT_PATH)
print('COMPILE_MODEL_PATH:', COMPILE_MODEL_PATH)
print('CHAR_SET_LEN: {}, CHAR_SET: {}'.format(CHAR_SET_LEN, CHAR_SET))
print('IMAGE_ORIGINAL_COLOR: {}'.format(IMAGE_ORIGINAL_COLOR))
print("MAX_CAPTCHA_LEN", MAX_CAPTCHA_LEN)
print('---------------------------------------------------------------------------------')
