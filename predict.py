#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import numpy as np
from config import ModelConfig


def decode_maps(charset):
    return {i: char for i, char in enumerate(charset, 0)}


def predict_func(image_batch, _sess, dense_decoded, _batch_size, _x, model: ModelConfig, split_char=None):
    if split_char is None:
        split_char = model.split_char
    image_batch = [np.reshape(image, [model.image_height, model.image_width, 1]) for image in image_batch]
    dense_decoded_code = _sess.run(dense_decoded, feed_dict={
        _batch_size: len(image_batch),
        _x: np.asarray(image_batch)
    })
    decoded_expression = []
    for item in dense_decoded_code:
        expression = ''

        for i in item:
            if i == -1:
                expression += ''
            else:
                expression += decode_maps(model.gen_charset)[i]
        decoded_expression.append(expression)
    return split_char.join(decoded_expression) if len(decoded_expression) > 1 else decoded_expression[0]
