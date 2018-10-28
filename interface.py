#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import tensorflow as tf

from graph_session import GraphSession
from predict import predict_func


class Interface(object):

    def __init__(self, graph_session: GraphSession):
        self.graph_sess = graph_session
        self.model_conf = graph_session.model_conf
        self.size_str = self.model_conf.size_string
        self.graph_name = self.graph_sess.graph_name
        self.sess = self.graph_sess.session
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
        return self.graph_name

    @property
    def size(self):
        return self.size_str

    def destroy(self):
        self.graph_sess.destroy()

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

    def __init__(self, interface: Interface=None):
        self.group = []
        self.set_default(interface)

    def add(self, interface: Interface):
        if interface in self.group:
            return
        self.group.append(interface)

    def remove(self, interface: Interface):
        if interface in self.group:
            interface.destroy()
            self.group.remove(interface)

    def remove_by_name(self, graph_name):
        interface = self.get_by_name(graph_name, False)
        self.remove(interface)

    def get_by_size(self, size: str, return_default=True):
        for interface in self.group:
            if interface.size_str == size:
                return interface
        return self.default if return_default else None

    def get_by_name(self, key: str, return_default=True):
        for interface in self.group:
            if interface.name == key:
                return interface
        return self.default if return_default else None

    @property
    def default(self):
        return self.group[0] if len(self.group) > 0 else None

    def set_default(self, interface: Interface):
        if not interface:
            return
        if len(self.group) > 0:
            self.group.pop(0)
        self.group.insert(0, interface)


