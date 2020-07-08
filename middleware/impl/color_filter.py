#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import io
import cv2
import time
import PIL.Image as PilImage
import numpy as np
import onnxruntime as ort
from enum import Enum, unique
from distutils.version import StrictVersion
from middleware.resource import color_model


@unique
class TargetColor(Enum):
    Red = 1
    Blue = 2
    Yellow = 3
    Black = 4


color_map = {
    'black': TargetColor.Black,
    'red': TargetColor.Red,
    'blue': TargetColor.Blue,
    'yellow': TargetColor.Yellow,
}


class ColorFilter:

    def __init__(self):
        self.model_onnx = color_model
        self.sess = ort.InferenceSession(self.model_onnx)

    def predict_color(self, image_batch, color: TargetColor):
        dense_decoded_code = self.sess.run(["dense_decoded:0"], input_feed={
            "input:0": image_batch,
        })
        result = dense_decoded_code[0][0].tolist()
        return [i for i, c in enumerate(result) if c == color.value]


if __name__ == '__main__':

    pass
    # import os
    # source_dir = r'E:\***'
    # target_dir = r'E:\***'
    # if not os.path.exists(target_dir):
    #     os.makedirs(target_dir)
    #
    # source_names = os.listdir(source_dir)
    # color_extract = ColorExtract()
    # st = time.time()
    # for i, name in enumerate(source_names):
    #     img_path = os.path.join(source_dir, name)
    #     if i % 100 == 0:
    #         print(i)
    #     with open(img_path, "rb") as f:
    #         b = f.read()
    #         result = color_extract.separate_color(b, color_map['red'])
    #     target_path = os.path.join(target_dir, name)
    #     with open(target_path, "wb") as f:
    #         f.write(result)
    #
    # print('completed {}'.format(time.time() - st))
