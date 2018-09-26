#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import base64
import binascii
import imghdr
import io

import tensorflow as tf
from PIL import Image as PIL_Image
from tensorflow.python.framework.errors_impl import NotFoundError

from config import *
from handler import preprocessing
from predict import predict_func

os.environ['CUDA_VISIBLE_DEVICES'] = DEVICE
sess = tf.Session()
try:
    with tf.gfile.GFile(COMPILE_MODEL_PATH, "rb") as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        _ = tf.import_graph_def(graph_def, name="")
except NotFoundError:
    exception('The system cannot find the model specified.')

init = tf.global_variables_initializer()
sess.run(init)

predict = sess.graph.get_tensor_by_name("output/predict:0")
x = sess.graph.get_tensor_by_name('input:0')
keep_prob = sess.graph.get_tensor_by_name('keep_prob:0')

print('Session Init')


def predict_b64(base64_img):
    # result, code, success = None, 200, True
    try:
        image_bytes = base64.b64decode(base64_img.encode('utf-8'))
    except binascii.Error:
        return None, 50002, False
    img_type = imghdr.what(None, h=image_bytes)
    if not img_type:
        return None, 50001, False
    try:
        result = predict_byte(image_bytes)
        return result, 200, True
    except OSError:
        return None, 50003, False
    except ValueError as e:
        print(e)
        return None, 50004, False


def predict_byte(image_bytes):
    data_stream = io.BytesIO(image_bytes)
    pil_image = PIL_Image.open(data_stream)
    origin_size = pil_image.size
    define_size = RESIZE if RESIZE else origin_size
    if define_size != origin_size:
        pil_image = pil_image.resize(define_size)
        origin_size = pil_image.size
    define_size = (origin_size[0] * MAGNIFICATION, origin_size[1] * MAGNIFICATION)
    if define_size != origin_size:
        pil_image = pil_image.resize(define_size)

    captcha_image = preprocessing(
        pil_image,
        binaryzation=BINARYZATION,
        smooth=SMOOTH,
        blur=BLUR,
        original_color=IMAGE_ORIGINAL_COLOR,
        invert=INVERT
    )
    image = captcha_image.flatten() / 255
    predict_text = predict_func(image, sess, predict, x, keep_prob)
    return predict_text
