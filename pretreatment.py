#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import cv2


class Pretreatment(object):

    def __init__(self, origin):
        self.origin = origin

    def get(self):
        return self.origin

    def binarization(self, value, modify=False):
        ret, _binarization = cv2.threshold(self.origin, value, 255, cv2.THRESH_BINARY)
        if modify:
            self.origin = _binarization
        return _binarization


def preprocessing(image, binaryzation=-1):
    pretreatment = Pretreatment(image)
    if binaryzation > 0:
        pretreatment.binarization(binaryzation, True)
    return pretreatment.get()


def preprocessing_by_func(exec_map, key, src_arr):
    if not exec_map:
        return src_arr
    target_arr = cv2.cvtColor(src_arr, cv2.COLOR_RGB2BGR)
    for sentence in exec_map.get(key):
        if sentence.startswith("@@"):
            target_arr = eval(sentence[2:])
        elif sentence.startswith("$$"):
            exec(sentence[2:])
    return cv2.cvtColor(target_arr, cv2.COLOR_BGR2RGB)


if __name__ == '__main__':
    pass
