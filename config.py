#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import re
import sys

import yaml

from character import *
from exception import exception

MODEL_CONFIG_PATH = 'model.yaml'
MODEL_PATH = 'model'

if not os.path.exists(MODEL_CONFIG_PATH):
    exception('Configuration File "{}" No Found.'.format(MODEL_CONFIG_PATH))

with open(MODEL_CONFIG_PATH, 'r', encoding="utf-8") as sys_fp:
    sys_stream = sys_fp.read()
    cf_model = yaml.load(sys_stream)


def char_set(_name):
    if _name == 'NUMERIC':
        return NUMBER
    elif _name == 'ALPHANUMERIC':
        return NUMBER + ALPHA_LOWER + ALPHA_UPPER
    elif _name == 'ALPHANUMERIC_LOWER':
        return NUMBER + ALPHA_LOWER
    elif _name == 'ALPHANUMERIC_UPPER':
        return NUMBER + ALPHA_UPPER
    else:
        return NUMBER + ALPHA_LOWER + ALPHA_UPPER


def __type(_object, _abbreviate=False):
    return re.findall(r"(?<=').*?(?=')", str(type(_object)))[0]


DEVICE = cf_model['System'].get('Device')
DEVICE = DEVICE if DEVICE else "cpu:0"

CHAR_SET = cf_model['Model'].get('CharSet')
GEN_CHAR_SET = char_set(CHAR_SET) if isinstance(CHAR_SET, str) else CHAR_SET
CHAR_SET_LEN = len(GEN_CHAR_SET)

TARGET_MODEL = cf_model['Model'].get('ModelName')

MAX_CAPTCHA_LEN = cf_model['Model'].get('CharLength')

IMAGE_CHANNEL = cf_model['Model'].get('ImageChannel')

MAGNIFICATION = cf_model['Pretreatment'].get('Magnification')
MAGNIFICATION = MAGNIFICATION if MAGNIFICATION and MAGNIFICATION > 0 and isinstance(MAGNIFICATION, int) else 1
IMAGE_ORIGINAL_COLOR = cf_model['Pretreatment'].get('OriginalColor')
BINARYZATION = cf_model['Pretreatment'].get('Binaryzation')
SMOOTH = cf_model['Pretreatment'].get('Smoothing')
BLUR = cf_model['Pretreatment'].get('Blur')
INVERT = cf_model['Pretreatment'].get('Invert')

COMPILE_MODEL_PATH = os.path.join(MODEL_PATH, '{}.pb'.format(TARGET_MODEL))

print('COMPILE_MODEL_PATH:', COMPILE_MODEL_PATH)
print('Loading Configuration...')
print('---------------------------------------------------------------------------------')
# print("PROJECT_PARENT_PATH", PROJECT_PARENT_PATH)
print('COMPILE_MODEL_PATH:', COMPILE_MODEL_PATH)
print('CHAR_SET_LEN: {}, CHAR_SET: {}'.format(CHAR_SET_LEN, CHAR_SET))
print('IMAGE_ORIGINAL_COLOR: {}'.format(IMAGE_ORIGINAL_COLOR))
print("MAX_CAPTCHA_LEN", MAX_CAPTCHA_LEN)
print('---------------------------------------------------------------------------------')
