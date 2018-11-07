#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os

from graph_session import GraphSession
from predict import predict_func

os.environ["CUDA_VISIBLE_DEVICES"] = "0"


class Interface(object):

    def __init__(self, graph_session: GraphSession):
        self.graph_sess = graph_session
        self.model_conf = graph_session.model_conf
        self.size_str = self.model_conf.size_string
        self.graph_name = self.graph_sess.graph_name
        self.model_type = self.graph_sess.model_type
        self.sess = self.graph_sess.session
        self.dense_decoded = self.sess.graph.get_tensor_by_name("dense_decoded:0")
        self.x = self.sess.graph.get_tensor_by_name('input:0')
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
            self.x,
            self.model_conf,
            split_char
        )
        return predict_text


class InterfaceManager(object):

    def __init__(self, interface: Interface = None):
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
        for interface in self.group:
            if self.size_fuzzy_matching(interface.size_str, size):
                return interface
        return self.default if return_default else None

    def get_by_type_size(self, size: str, model_type: str, return_default=True):
        for interface in self.group:
            if interface.size_str == size and interface.model_type == model_type:
                return interface
        for interface in self.group:
            if self.size_fuzzy_matching(interface.size_str, size) and interface.model_type == model_type:
                return interface
        return self.get_by_type(size, return_default=return_default)

    def get_by_type(self, model_type: str, return_default=True):
        for interface in self.group:
            if interface.model_type == model_type:
                return interface
        return self.default if return_default else None

    def get_by_name(self, key: str, return_default=True):
        for interface in self.group:
            if interface.name == key:
                return interface
        return self.default if return_default else None

    @staticmethod
    def size_fuzzy_matching(source_size: str, target_size: str):
        _source_size = [int(int(_) / 10 + 0.5) * 10 for _ in source_size.split('x')]
        _target_size = [int(int(_) / 10 + 0.5) * 10 for _ in target_size.split('x')]
        if _source_size == _target_size:
            return True
        return False

    @property
    def default(self):
        return self.group[0] if len(self.group) > 0 else None

    @property
    def default_name(self):
        _default = self.default
        if not _default:
            return
        return _default.graph_name

    def set_default(self, interface: Interface):
        if not interface:
            return
        self.group.insert(0, interface)
