#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import numpy as np
from config import ModelConfig


def decode_maps(charset):
    return {i: char for i, char in enumerate(charset, 0)}


def predict_func(captcha_image, _sess, dense_decoded, _x, model: ModelConfig):
    captcha_image = np.reshape(captcha_image, [model.image_height, model.image_width, 1])
    dense_decoded_code = _sess.run(dense_decoded, feed_dict={_x: np.asarray([captcha_image])})
    decoded_expression = []
    for item in dense_decoded_code:
        expression = ''

        for i in item:
            if i == -1:
                expression += ''
            else:
                expression += decode_maps(model.gen_charset)[i]
        decoded_expression.append(expression)
    return decoded_expression[0]
