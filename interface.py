#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import cv2
import base64
import binascii
import imghdr
import io
import numpy as np
import tensorflow as tf
from PIL import Image as PIL_Image
from tensorflow.python.framework.errors_impl import NotFoundError
from pretreatment import preprocessing
from config import *
from constants import RequestException
from predict import predict_func

sess = tf.Session()
init = tf.global_variables_initializer()
sess.run(init)


class Interface(object):

    def __init__(self, model: ModelConfig):
        self.model = model
        self.predict = None
        self.x = None
        self.seq_len = None
        try:
            with tf.gfile.GFile(model.compile_model_path, "rb") as f:
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(f.read())
                _ = tf.import_graph_def(graph_def, name="")
        except NotFoundError:
            exception('The system cannot find the model specified.')
        self.load()

    def load(self):
        self.predict = sess.graph.get_tensor_by_name("lstm/output/predict:0")
        self.x = sess.graph.get_tensor_by_name('input:0')
        self.seq_len = sess.graph.get_tensor_by_name('lstm/seq_len:0')
        print('Session Init')

    def predict_b64(self, base64_img):
        e = RequestException()
        # result, code, success = None, 200, True
        try:
            image_bytes = base64.b64decode(base64_img.encode('utf-8'))
        except binascii.Error:
            return e.INVALID_BASE64_STRING['message'], e.INVALID_BASE64_STRING['code'], False
        img_type = imghdr.what(None, h=image_bytes)
        if not img_type:
            return e.INVALID_IMAGE_FORMAT['message'], e.INVALID_IMAGE_FORMAT['code'], False
        try:
            result = self.predict_byte(image_bytes)
            return result, 200, True
        except OSError:
            return e.IMAGE_DAMAGE['message'], e.IMAGE_DAMAGE['code'], False
        except ValueError as _e:
            print(_e)
            return e.IMAGE_SIZE_NOT_MATCH_GRAPH['message'], e.IMAGE_SIZE_NOT_MATCH_GRAPH['code'], False

    def predict_byte(self, image_bytes):
        data_stream = io.BytesIO(image_bytes)
        pil_image = PIL_Image.open(data_stream).convert('RGB')

        image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2GRAY)
        image = preprocessing(image, self.model.binaryzation, self.model.smooth, self.model.blur).astype(np.float32) / 255.
        image = cv2.resize(image, (self.model.image_width, self.model.image_height))

        decoded, log_prob = tf.nn.ctc_beam_search_decoder(
            self.predict,
            self.seq_len,
            merge_repeated=False,
        )
        dense_decoded = tf.sparse_tensor_to_dense(decoded[0], default_value=-1)
        predict_text = predict_func(image, sess, dense_decoded, self.x, self.model)
        return predict_text
