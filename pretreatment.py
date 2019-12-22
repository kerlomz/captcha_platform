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


if __name__ == '__main__':
    pass
