#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import numpy as np
from config import ModelConfig
from handler import vec2text


def predict_func(captcha_image, _sess, _predict, _x, _keep_prob, model: ModelConfig):
    text_list = _sess.run(_predict, feed_dict={_x: [captcha_image], _keep_prob: 1})
    text = text_list[0].tolist()
    vector = np.zeros(model.max_captcha_len * model.charset_len)
    i = 0
    for n in text:
        vector[i * model.charset_len + n] = 1
        i += 1
    return vec2text(vector, model.charset_len, model.gen_charset)
