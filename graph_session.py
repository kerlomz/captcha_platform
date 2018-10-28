#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import tensorflow as tf
from config import ModelConfig
from tensorflow.python.framework.errors_impl import NotFoundError


class GraphSession(object):
    def __init__(self, model_conf: ModelConfig):
        self.model_conf = model_conf
        self.logger = self.model_conf.logger
        self.size_str = self.model_conf.size_string
        self.model_name = self.model_conf.target_model
        self.graph_name = self.model_conf.graph_name
        self.model_type = self.model_conf.model_type
        self.graph = tf.Graph()
        self.sess = tf.Session(graph=self.graph)
        self.graph_def = self.graph.as_graph_def()
        self.load_model()

    def load_model(self):
        try:
            with tf.gfile.GFile(self.model_conf.compile_model_path, "rb") as f:
                graph_def_file = f.read()
            self.graph_def.ParseFromString(graph_def_file)
        except NotFoundError:
            self.logger.error('The system cannot find the model specified.')
            self.sess = None
            return

        with self.graph.as_default():
            self.sess.run(tf.global_variables_initializer())
            _ = tf.import_graph_def(self.graph_def, name="")

        # self.logger.info('TensorFlow Session {} Loaded.'.format(self.model_conf.target_model))

    @property
    def session(self):
        return self.sess

    def destroy(self):
        self.sess.close()
        del self.sess
