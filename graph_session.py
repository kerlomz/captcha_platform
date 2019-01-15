#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import io
import cv2
import numpy as np
import PIL.Image
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
        # if self.model_conf.color_engine == 'k-means':
        self.color_graph = tf.Graph()
        self.color_sess = tf.Session(graph=self.color_graph)
        self.loaded = self.load_model()

        with self.color_graph.as_default():
            self.img_holder = tf.placeholder(dtype=tf.int32)
            self.black = tf.constant([[0, 0, 0]], dtype=tf.int32, name='black')
            self.red = tf.constant([[0, 0, 255]], dtype=tf.int32, name='red')
            self.yellow = tf.constant([[0, 255, 255]], dtype=tf.int32, name='yellow')
            self.blue = tf.constant([[255, 0, 0]], dtype=tf.int32, name='blue')
            self.green = tf.constant([[0, 255, 0]], dtype=tf.int32, name='green')

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

    def k_means(self, data, target_color, bg_color1, bg_color2, alpha=1.0):
        def get_distance(point):
            sum_squares = tf.cast(
                tf.reduce_sum(
                    tf.abs(tf.subtract(data, point)),
                    axis=2,
                    keepdims=True
                ),
                tf.float32)
            return sum_squares

        with self.color_graph.as_default():
            alpha_value = tf.constant(alpha, dtype=tf.float32)
            black_distance = get_distance(self.black)
            red_distance = get_distance(self.red)
            if target_color == 1:
                red_distance = tf.multiply(red_distance, alpha_value)
            blue_distance = get_distance(self.blue)
            if target_color == 2:
                blue_distance = tf.multiply(blue_distance, alpha_value)
            yellow_distance = get_distance(self.yellow)
            if target_color == 3:
                yellow_distance = tf.multiply(yellow_distance, alpha_value)

            green_distance = get_distance(self.green)
            c_1_distance = get_distance(bg_color1)
            c_2_distance = get_distance(bg_color2)

            distances = tf.concat(
                [black_distance, red_distance, blue_distance, yellow_distance, green_distance, c_1_distance,
                 c_2_distance], axis=-1)

            clusters = tf.cast(tf.argmin(distances, axis=-1), tf.int32)

            mask = tf.equal(clusters, target_color)
            mask = tf.cast(mask, tf.int32)
            return mask * 255

    def filter_img(self, img, target_color, alpha=0.9):
        with self.color_graph.as_default():
            # background color1
            color_1 = img[0, 0, :]
            color_1 = tf.reshape(color_1, [1, 3])
            color_1 = tf.cast(color_1, dtype=tf.int32)

            # background color2
            color_2 = img[34, 6, :]
            color_2 = tf.reshape(color_2, [1, 3])
            color_2 = tf.cast(color_2, dtype=tf.int32)

            filtered_img = self.k_means(self.img_holder, target_color, color_1, color_2, alpha)
            filtered_img = tf.expand_dims(filtered_img, axis=0)
            filtered_img = tf.expand_dims(filtered_img, axis=-1)
            filtered_img = tf.squeeze(filtered_img)
            return filtered_img

    def separate_color(self, image_bytes, color):
        image = np.asarray(bytearray(image_bytes), dtype="uint8")
        image = cv2.imdecode(image, -1)
        rgb = cv2.split(image)
        image = cv2.merge(rgb[:3])
        filtered = self.filter_img(self.img_holder, target_color=color, alpha=0.8)
        result = self.color_sess.run(filtered, {self.img_holder: image})
        return bytearray(cv2.imencode('.png', result)[1])

    @property
    def session(self):
        return self.sess

    def destroy(self):
        self.sess.close()
        self.color_sess.close()
        del self.sess
        del self.color_sess
