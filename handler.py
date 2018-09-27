#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>

import cv2
import numpy as np


def pos2char(char_idx, charset):
    return charset[char_idx]


def vec2text(vec, charset_len, gen_charset):
    char_pos = vec.nonzero()[0]
    text = []
    for i, c in enumerate(char_pos):
        char_idx = c % charset_len
        char_code = pos2char(char_idx, gen_charset)
        text.append(char_code)
    return "".join(text)


def preprocessing(pil_image, binaryzation=127, smooth=-1, blur=-1, original_color=False, invert=False):
    _pil_image = pil_image
    if not original_color:
        _pil_image = _pil_image.convert("L")
    image = np.array(_pil_image)
    if binaryzation > 0:
        ret, thresh = cv2.threshold(image, binaryzation, 255, cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY)
    else:
        thresh = image
    _image = thresh
    if smooth != -1:
        smooth = smooth + 1 if smooth % 2 == 0 else smooth
        _smooth = cv2.medianBlur(thresh, smooth)
        _image = _smooth
    if blur != -1:
        blur = blur + 1 if blur % 2 == 0 else blur
        _blur = cv2.GaussianBlur(_image if smooth != -1 else thresh, (blur, blur), 0)
        _image = _blur
    return _image
