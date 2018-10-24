#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import cv2
import base64
import binascii
import io
import numpy as np
import tensorflow as tf
from PIL import Image as PIL_Image
from tensorflow.python.framework.errors_impl import NotFoundError
from pretreatment import preprocessing
from config import *
from constants import RequestException
from predict import predict_func
from utils import ImageUtils


class Interface(object):

    def __init__(self, model: ModelConfig):
        self.model = model
        self.predict = None
        self.x = None
        self.sess = tf.Session(graph=tf.Graph())
        self.seq_len = None
        self.batch_size = None
        self.graph_def = self.sess.graph.as_graph_def()
        self.load()

    def load(self):
        try:
            with tf.gfile.GFile(self.model.compile_model_path, "rb") as f:
                graph_def_file = f.read()
            self.graph_def.ParseFromString(graph_def_file)
        except NotFoundError:
            exception('The system cannot find the model specified.')

        with self.sess.graph.as_default():
            self.sess.run(tf.global_variables_initializer())
            _ = tf.import_graph_def(self.graph_def, name="")

        self.predict = self.sess.graph.get_tensor_by_name("lstm/output/predict:0")
        self.x = self.sess.graph.get_tensor_by_name('input:0')
        self.seq_len = self.sess.graph.get_tensor_by_name('lstm/seq_len:0')
        self.batch_size = self.sess.graph.get_tensor_by_name('batch_size:0')
        print('Session Name: {} Inited.'.format(self.model.target_model))

    def close_session(self):
        self.sess.close()
        del self.sess

    def predict_b64(self, base64_img, func, split_char=None):
        e = RequestException()
        # result, code, success = None, 200, True
        try:
            if isinstance(base64_img, list):
                bytes_batch = [base64.b64decode(i.encode('utf-8')) for i in base64_img]
            else:
                bytes_batch = base64.b64decode(base64_img.encode('utf-8')).split(self.model.split_flag)
        except binascii.Error:
            return e.INVALID_BASE64_STRING['message'], e.INVALID_BASE64_STRING['code'], False
        what_img = [ImageUtils.test_image(i) for i in bytes_batch]
        if None in what_img:
            return e.INVALID_IMAGE_FORMAT['message'], e.INVALID_IMAGE_FORMAT['code'], False
        try:
            result = self.predict_byte(bytes_batch, split_char)
            return result, 200, True
        except OSError:
            return e.IMAGE_DAMAGE['message'], e.IMAGE_DAMAGE['code'], False
        except ValueError as _e:
            print(_e)
            return e.IMAGE_SIZE_NOT_MATCH_GRAPH['message'], e.IMAGE_SIZE_NOT_MATCH_GRAPH['code'], False

    def load_image(self, image_bytes):
        data_stream = io.BytesIO(image_bytes)
        pil_image = PIL_Image.open(data_stream).convert('RGB')
        image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2GRAY)
        image = preprocessing(image, self.model.binaryzation, self.model.smooth, self.model.blur)
        image = image.astype(np.float32) / 255.
        return cv2.resize(image, (self.model.image_width, self.model.image_height))

    def predict_byte(self, image_list, split_char=None):

        image_batch = [self.load_image(i) for i in image_list]

        decoded, log_prob = tf.nn.ctc_beam_search_decoder(
            self.predict,
            self.seq_len,
            merge_repeated=False,
        )
        dense_decoded = tf.sparse_tensor_to_dense(decoded[0], default_value=-1)
        predict_text = predict_func(image_batch, self.sess, dense_decoded, self.batch_size, self.x, self.model, split_char)
        return predict_text
