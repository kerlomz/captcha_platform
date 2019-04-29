#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import tensorflow as tf
from tensorflow.python.framework.graph_util import convert_variables_to_constants

black = tf.constant([[0, 0, 0]], dtype=tf.int32)
red = tf.constant([[0, 0, 255]], dtype=tf.int32)
yellow = tf.constant([[0, 255, 255]], dtype=tf.int32)
blue = tf.constant([[255, 0, 0]], dtype=tf.int32)
green = tf.constant([[0, 255, 0]], dtype=tf.int32)
white = tf.constant([[255, 255, 255]], dtype=tf.int32)


def k_means(data, target_color, bg_color1, bg_color2, alpha=1.0):
    def get_distance(point):
        sum_squares = tf.cast(tf.reduce_sum(tf.abs(tf.subtract(data, point)), axis=2, keep_dims=True), tf.float32)
        return sum_squares

    alpha_value = tf.constant(alpha, dtype=tf.float32)
    # target_color  black:0, red:1, blue:2, yellow:3, green:4, color_1:5, color_2:6
    black_distance = get_distance(black)
    red_distance = get_distance(red)
    if target_color == 1:
        red_distance = tf.multiply(red_distance, alpha_value)
    blue_distance = get_distance(blue)
    if target_color == 2:
        blue_distance = tf.multiply(blue_distance, alpha_value)
    yellow_distance = get_distance(yellow)
    if target_color == 3:
        yellow_distance = tf.multiply(yellow_distance, alpha_value)
    white_distance = get_distance(yellow)
    if target_color == 7:
        white_distance = tf.multiply(white_distance, alpha_value)

    green_distance = get_distance(green)
    c_1_distance = get_distance(bg_color1)
    c_2_distance = get_distance(bg_color2)

    distances = tf.concat([
        black_distance,
        red_distance,
        blue_distance,
        yellow_distance,
        green_distance,
        c_1_distance,
        c_2_distance,
        white_distance
    ], axis=-1)

    clusters = tf.cast(tf.argmin(distances, axis=-1), tf.int32)

    mask = tf.equal(clusters, target_color)
    mask = tf.cast(mask, tf.int32)

    return mask * 255


def filter_img(img, target_color, alpha=0.9):
    # background color1
    color_1 = img[0, 0, :]
    color_1 = tf.reshape(color_1, [1, 3])
    color_1 = tf.cast(color_1, dtype=tf.int32)

    # background color2
    color_2 = img[34, 6, :]
    color_2 = tf.reshape(color_2, [1, 3])
    color_2 = tf.cast(color_2, dtype=tf.int32)

    filtered_img = k_means(img_holder, target_color, color_1, color_2, alpha)
    filtered_img = tf.expand_dims(filtered_img, axis=0)
    filtered_img = tf.expand_dims(filtered_img, axis=-1)
    filtered_img = tf.squeeze(filtered_img, name="filtered")
    return filtered_img


def compile_graph():

    with sess.graph.as_default():
        input_graph_def = sess.graph.as_graph_def()

    output_graph_def = convert_variables_to_constants(
        sess,
        input_graph_def,
        output_node_names=['filtered']
    )

    last_compile_model_path = "color_extractor.pb"
    with tf.gfile.FastGFile(last_compile_model_path, mode='wb') as gf:
        # gf.write(output_graph_def.SerializeToString())
        print(output_graph_def.SerializeToString())


if __name__ == "__main__":

    sess = tf.Session()
    img_holder = tf.placeholder(dtype=tf.int32, name="img_holder")
    color = tf.placeholder(dtype=tf.int32, name="target_color")
    filtered = filter_img(img_holder, color, alpha=0.8)

    compile_graph()

