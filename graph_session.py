#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.python.framework.errors_impl import NotFoundError
from config import ModelConfig


class GraphSession(object):
    def __init__(self, model_conf: ModelConfig):
        self.model_conf = model_conf
        self.logger = self.model_conf.logger
        self.size_str = self.model_conf.size_string
        self.model_name = self.model_conf.target_model
        self.graph_name = self.model_conf.graph_name
        self.model_type = self.model_conf.model_type
        self.model_site = self.model_conf.model_site
        self.version = self.model_conf.version
        self.graph = tf.Graph()
        self.sess = tf.Session(
            graph=self.graph,
            config=tf.ConfigProto(
                allow_soft_placement=True,
                # log_device_placement=True,
                gpu_options=tf.GPUOptions(
                    # allow_growth=True,  # it will cause fragmentation.
                    per_process_gpu_memory_fraction=self.model_conf.device_usage
                ))
        )
        self.graph_def = self.graph.as_graph_def()
        self.hsv_map = {
            "blue": {
                "lower_hsv": np.array([100, 128, 46]),
                "high_hsv": np.array([124, 255, 255])
            },
            "red": {
                "lower_hsv": np.array([0, 128, 46]),
                "high_hsv": np.array([5, 255, 255])
            },
            "yellow": {
                "lower_hsv": np.array([15, 128, 46]),
                "high_hsv": np.array([34, 255, 255])
            },
            "green": {
                "lower_hsv": np.array([35, 128, 46]),
                "high_hsv": np.array([77, 255, 255])
            },
            "black": {
                "lower_hsv": np.array([0, 0, 0]),
                "high_hsv": np.array([180, 255, 46])
            }
        }
        self.loaded = self.load_model()

    def load_model(self):
        # Here is for debugging, positioning error source use.
        # with self.graph.as_default():
        #     saver = tf.train.import_meta_graph('graph/***.meta')
        #     saver.restore(self.sess, tf.train.latest_checkpoint('graph'))
        if not self.model_conf.model_exists:
            self.destroy()
            return False
        try:
            with tf.gfile.GFile(self.model_conf.compile_model_path, "rb") as f:
                graph_def_file = f.read()
            self.graph_def.ParseFromString(graph_def_file)
            with self.graph.as_default():
                self.sess.run(tf.global_variables_initializer())
                _ = tf.import_graph_def(self.graph_def, name="")

            self.logger.info('TensorFlow Session {} Loaded.'.format(self.model_conf.target_model))
            return True
        except NotFoundError:
            self.logger.error('The system cannot find the model specified.')
            self.destroy()
            return False

    def separate_color(self, image_bytes, color):
        image = np.asarray(bytearray(image_bytes), dtype="uint8")
        image = cv2.imdecode(image, -1)
        hsv = cv2.cvtColor(np.asarray(image), cv2.COLOR_BGR2HSV)
        lower_hsv = self.hsv_map[color]['lower_hsv']
        high_hsv = self.hsv_map[color]['high_hsv']
        mask = cv2.inRange(hsv, lowerb=lower_hsv, upperb=high_hsv)
        mask = bytearray(cv2.imencode('.png', mask)[1])
        return mask

    @property
    def session(self):
        return self.sess

    def destroy(self):
        self.sess.close()
        del self.sess
