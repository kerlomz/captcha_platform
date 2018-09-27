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
from constants import RequestException
from handler import preprocessing
from predict import predict_func

sess = tf.Session()
init = tf.global_variables_initializer()
sess.run(init)


class Interface(object):

    def __init__(self, model: ModelConfig):
        self.model = model
        self.predict = None
        self.x = None
        self.keep_prob = None
        # os.environ['CUDA_VISIBLE_DEVICES'] = model.DEVICE
        try:
            with tf.gfile.GFile(model.compile_model_path, "rb") as f:
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(f.read())
                _ = tf.import_graph_def(graph_def, name="")
        except NotFoundError:
            exception('The system cannot find the model specified.')
        self.load()

    def load(self):
        self.predict = sess.graph.get_tensor_by_name("output/predict:0")
        self.x = sess.graph.get_tensor_by_name('input:0')
        self.keep_prob = sess.graph.get_tensor_by_name('keep_prob:0')
        print('Session Init')

    def predict_b64(self, base64_img):
        _exception = RequestException()
        # result, code, success = None, 200, True
        try:
            image_bytes = base64.b64decode(base64_img.encode('utf-8'))
        except binascii.Error:
            return _exception.INVALID_BASE64_STRING['message'], _exception.INVALID_BASE64_STRING['code'], False
        img_type = imghdr.what(None, h=image_bytes)
        if not img_type:
            return _exception.INVALID_IMAGE_FORMAT['message'], _exception.INVALID_IMAGE_FORMAT['code'], False
        try:
            result = self.predict_byte(image_bytes)
            return result, 200, True
        except OSError:
            return _exception.IMAGE_DAMAGE['message'], _exception.IMAGE_DAMAGE['code'], False
        except ValueError as e:
            print(e)
            return _exception.IMAGE_SIZE_NOT_MATCH_GRAPH['message'], _exception.IMAGE_SIZE_NOT_MATCH_GRAPH[
                'code'], False

    def predict_byte(self, image_bytes):
        data_stream = io.BytesIO(image_bytes)
        pil_image = PIL_Image.open(data_stream)
        origin_size = pil_image.size
        define_size = self.model.resize if self.model.resize else origin_size
        if define_size != origin_size:
            pil_image = pil_image.resize(define_size)
            origin_size = pil_image.size
        define_size = (origin_size[0] * self.model.magnification, origin_size[1] * self.model.magnification)
        if define_size != origin_size:
            pil_image = pil_image.resize(define_size)

        captcha_image = preprocessing(
            pil_image,
            binaryzation=self.model.binaryzation,
            smooth=self.model.smooth,
            blur=self.model.blur,
            original_color=self.model.image_original_color,
            invert=self.model.invert
        )
        image = captcha_image.flatten() / 255
        predict_text = predict_func(image, sess, self.predict, self.x, self.keep_prob, self.model)
        return predict_text
