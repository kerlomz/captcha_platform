#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
from config import ModelConfig


def decode_maps(categories):
    return {index: category for index, category in enumerate(categories, 0)}


def predict_func(image_batch, _sess, dense_decoded, op_input, model: ModelConfig, output_split=None):

    output_split = model.output_split if output_split is None else output_split

    category_split = model.category_split if model.category_split else ""

    dense_decoded_code = _sess.run(dense_decoded, feed_dict={
        op_input: image_batch,
    })
    decoded_expression = []
    for item in dense_decoded_code:
        expression = []

        for i in item:
            if i == -1 or i == model.category_num:
                expression.append("")
            else:
                expression.append(decode_maps(model.category)[i])
        decoded_expression.append(category_split.join(expression))
    return output_split.join(decoded_expression) if len(decoded_expression) > 1 else decoded_expression[0]
