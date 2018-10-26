#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import tensorflow as tf

from config import *
from graph_session import GraphSessionPool
from predict import predict_func


class Interface(object):

    def __init__(self, model_conf: ModelConfig, model_sess_pool: GraphSessionPool):
        self.model_conf = model_conf
        self.model_sess_pool = model_sess_pool
        self.size_str = self.model_conf.size_string
        self.model_name = "{}&{}".format(self.model_conf.target_model, self.size_str)
        self.model_sess = model_sess_pool.get(self.model_name)
        self.sess = self.model_sess.sess
        self.predict = self.sess.graph.get_tensor_by_name("lstm/output/predict:0")
        self.x = self.sess.graph.get_tensor_by_name('input:0')
        self.seq_len = self.sess.graph.get_tensor_by_name('lstm/seq_len:0')
        self.batch_size = self.sess.graph.get_tensor_by_name('batch_size:0')
        decoded, log_prob = tf.nn.ctc_beam_search_decoder(
            self.predict,
            self.seq_len,
            merge_repeated=False,
        )
        self.dense_decoded = tf.sparse_tensor_to_dense(decoded[0], default_value=-1)
        self.sess.graph.finalize()

    @property
    def name(self):
        return self.model_name

    @property
    def size(self):
        return self.size_str

    def destroy(self):
        self.model_sess_pool.destroy(self.model_name)

    def predict_batch(self, image_batch, split_char=None):
        predict_text = predict_func(
            image_batch,
            self.sess,
            self.dense_decoded,
            self.batch_size,
            self.x,
            self.model_conf,
            split_char
        )
        return predict_text


class InterfaceManager(object):

    def __init__(self, default: Interface=None):
        self.group = set()
        self._default = default

    def add(self, interface: Interface):
        if interface in self.group:
            return
        self.group.add(interface)

    def remove(self, interface: Interface):
        if interface in self.group:
            interface.destroy()
            self.group.remove(interface)

    def get_by_size(self, size: str):
        for interface in self.group:
            if interface.size_str == size:
                return interface
        return self._default

    def get_by_key(self, key: str):
        for interface in self.group:
            if interface.name == key:
                return interface
        return self._default

    @property
    def default(self):
        return self._default

    def set_default(self, interface):
        self.remove(self._default)
        self.group.add(interface)
        self._default = interface

