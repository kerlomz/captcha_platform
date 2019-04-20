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
        self.model_type = self.graph_sess.model_type
        self.model_site = self.graph_sess.model_site
        self.version = self.graph_sess.version
        self.model_charset = self.model_conf.charset
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

    def get_by_sites(self, model_site, size: str, return_default=True, strict=True):
        match_ids = [i for i in range(len(self.group)) if (
            model_site in self.group[i].model_site
            if strict
            else model_site in self.group[i].model_site and size == self.group[i].size_str
        )]
        max_id = match_ids[0] if match_ids else 0
        for i in match_ids:
            interface = self.group[i]
            if interface.version > self.group[i].version:
                max_id = i
        return self.group[max_id] if match_ids else self.get_by_size(size) if return_default else None

    def get_by_size(self, size: str, return_default=True):

        match_ids = [i for i in range(len(self.group)) if self.group[i].size_str == size]
        max_id = match_ids[0] if match_ids else 0
        for i in match_ids:
            interface = self.group[i]
            if interface.version > self.group[i].version:
                max_id = i
        return self.group[max_id] if match_ids else self.default if return_default else None

    def get_by_type_size(self, size: str, model_type: str, return_default=True):
        match_ids = [
            i for i in range(len(self.group))
            if self.group[i].size_str == size and self.group[i].model_type == model_type
        ]
        max_id = match_ids[0] if match_ids else 0
        for i in match_ids:
            interface = self.group[i]
            if interface.version > self.group[i].version:
                max_id = i
        return self.group[max_id] if match_ids else self.get_by_type(model_type, return_default)

    def get_by_type(self, model_type: str, return_default=True):
        match_ids = [i for i in range(len(self.group)) if self.group[i].model_type == model_type]
        max_id = match_ids[0] if match_ids else 0
        for i in match_ids:
            interface = self.group[i]
            if interface.version > self.group[i].version:
                max_id = i
        return self.group[max_id] if match_ids else self.default if return_default else None

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

    @property
    def support_sites(self):
        support = [i.model_site for i in self.group]
        return [j for i in support for j in i]

    def set_default(self, interface: Interface):
        if not interface:
            return
        self.group.insert(0, interface)
