#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import numpy as np
import cv2


def rgb_filter(image_obj, need_rgb):
    low_rgb = np.array([i-15 for i in need_rgb])
    high_rgb = np.array([i+15 for i in need_rgb])
    mask = cv2.inRange(image_obj, lowerb=low_rgb, upperb=high_rgb)
    mask = cv2.bitwise_not(mask)
    mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    # img_bytes = cv2.imencode('.png', mask)[1]
    return mask


if __name__ == '__main__':
    pass