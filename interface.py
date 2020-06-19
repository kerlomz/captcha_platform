#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import time
from graph_session import GraphSession
from predict import predict_func

os.environ["CUDA_VISIBLE_DEVICES"] = "0"


class Interface(object):

    def __init__(self, graph_session: GraphSession):
        self.graph_sess = graph_session
        self.model_conf = graph_session.model_conf
        self.size_str = self.model_conf.size_string
        self.graph_name = self.graph_sess.graph_name
        self.version = self.graph_sess.version
        self.model_category = self.model_conf.category_param
        if self.graph_sess.loaded:
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

    def predict_batch(self, image_batch, output_split=None):
        predict_text = predict_func(
            image_batch,
            self.sess,
            self.dense_decoded,
            self.x,
            self.model_conf,
            output_split
        )
        return predict_text


class InterfaceManager(object):

    def __init__(self, interface: Interface = None):
        self.group = []
        self.invalid_group = {}
        self.set_default(interface)

    def add(self, interface: Interface):
        if interface in self.group:
            return
        self.group.append(interface)

    def remove(self, interface: Interface):
        if interface in self.group:
            interface.destroy()
            self.group.remove(interface)

    def report(self, model):
        self.invalid_group[model] = {"create_time": time.asctime(time.localtime(time.time()))}

    def remove_by_name(self, graph_name):
        interface = self.get_by_name(graph_name, False)
        self.remove(interface)

    def get_by_size(self, size: str, return_default=True):

        match_ids = [i for i in range(len(self.group)) if self.group[i].size_str == size]
        if not match_ids:
            return self.default if return_default else None
        else:
            ver = [self.group[i].version for i in match_ids]
            return self.group[match_ids[ver.index(max(ver))]]

    def get_by_name(self, key: str, return_default=True):
        for interface in self.group:
            if interface.name == key:

                return interface
        return self.default if return_default else None

    @property
    def default(self):
        return self.group[0] if len(self.group) > 0 else None

    @property
    def default_name(self):
        _default = self.default
        if not _default:
            return
        return _default.graph_name

    @property
    def total(self):
        return len(self.group)

    @property
    def online_names(self):
        return [i.name for i in self.group]

    def set_default(self, interface: Interface):
        if not interface:
            return
        self.group.insert(0, interface)
