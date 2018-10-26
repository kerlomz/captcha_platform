#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import tensorflow as tf
from config import ModelConfig
from tensorflow.python.framework.errors_impl import NotFoundError


class GraphSession(object):
    def __init__(self, model: ModelConfig):
        self.model = model
        self.size_str = self.model.size_string
        self.name = self.model.target_model
        self.key_name = "{}&{}".format(self.name, self.size_str)
        self.graph = tf.Graph()
        self._sess = tf.Session(graph=self.graph)
        self.graph_def = self.graph.as_graph_def()
        self.load_model()

    def load_model(self):
        try:
            with tf.gfile.GFile(self.model.compile_model_path, "rb") as f:
                graph_def_file = f.read()
            self.graph_def.ParseFromString(graph_def_file)
        except NotFoundError:
            print('The system cannot find the model specified.')
            self._sess = None
            return

        with self.graph.as_default():
            self._sess.run(tf.global_variables_initializer())
            _ = tf.import_graph_def(self.graph_def, name="")

        print('TensorFlow Session {} Loaded.'.format(self.model.target_model))

    @property
    def sess(self):
        return self._sess

    def destroy(self):
        self._sess.close()
        del self._sess


class GraphSessionPool(object):

    def __init__(self, default: GraphSession=None):
        self.pool = {}
        self.set_default(default)

    def set_default(self, default: GraphSession=None):
        if not default:
            return
        self.pool['default'] = default

    def add(self, model_sess: GraphSession):
        key = model_sess.key_name
        if not model_sess.sess:
            return
        if key in self.pool:
            return
        self.pool[key] = model_sess

    def get(self, key: str):
        if key not in self.pool:
            return self.pool['default']
        return self.pool.get(key)

    def destroy(self, key: str):
        model = self.pool.get(key)
        if not model:
            raise Exception('model no found!')
        else:
            model['sess'].destroy()
            self.pool.pop(key)

    def reset(self):
        for i in self.pool:
            i['sess'].destroy()

    def find_by_size_str(self, size_str: str):
        return [v for k, v in self.pool.items() if str(k).endswith(size_str)]

    def find_by_size(self, width: int, height: int):
        size_str = "{}x{}".format(width, height)
        return self.find_by_size_str(size_str)

    def get_by_name(self, name: str):
        return [v for k, v in self.pool.items() if str(k).startswith(name)]
