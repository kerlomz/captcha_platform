#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import io
import cv2
import time
import base64
import binascii
import datetime
import hashlib
import numpy as np
from PIL import Image as PIL_Image
from constants import Response
from pretreatment import preprocessing


class SignUtils(object):

    @staticmethod
    def md5(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def timestamp():
        return int(time.mktime(datetime.datetime.now().timetuple()))


class ImageUtils(object):

    def __init__(self, model):
        self.model = model

    def get_image_batch(self, base64_img):
        response = Response()
        try:
            if isinstance(base64_img, list):
                bytes_batch = [base64.b64decode(i.encode('utf-8')) for i in base64_img]
            else:
                bytes_batch = base64.b64decode(base64_img.encode('utf-8')).split(self.model.split_flag)
        except binascii.Error:
            return None, response.INVALID_BASE64_STRING
        what_img = [ImageUtils.test_image(i) for i in bytes_batch]
        if None in what_img:
            return None, response.INVALID_IMAGE_FORMAT
        try:
            image_batch = [self.load_image(i) for i in bytes_batch]
            return image_batch, response.SUCCESS
        except OSError:
            return None, response.IMAGE_DAMAGE
        except ValueError as _e:
            print(_e)
            return None, response.IMAGE_SIZE_NOT_MATCH_GRAPH

    def load_image(self, image_bytes):
        data_stream = io.BytesIO(image_bytes)
        pil_image = PIL_Image.open(data_stream).convert('RGB')
        image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2GRAY)
        image = preprocessing(image, self.model.binaryzation, self.model.smooth, self.model.blur)
        image = image.astype(np.float32) / 255.
        return cv2.resize(image, (self.model.image_width, self.model.image_height))

    @staticmethod
    def test_image(h):
        """JPEG data in JFIF format"""
        if h[6:10] == b'JFIF':
            return 'jpeg'
        """JPEG data in Exif format"""
        if h[6:10] == b'Exif':
            return 'jpeg'
        """PNG"""
        if h[:8] == b"\211PNG\r\n\032\n":
            return 'png'
        """GIF ('87 and '89 variants)"""
        if h[:6] in (b'GIF87a', b'GIF89a'):
            return 'gif'
        """TIFF (can be in Motorola or Intel byte order)"""
        if h[:2] in (b'MM', b'II'):
            return 'tiff'
        if h[:2] == b'BM':
            return 'bmp'
        """SGI image library"""
        if h[:2] == b'\001\332':
            return 'rgb'
        """PBM (portable bitmap)"""
        if len(h) >= 3 and \
                h[0] == b'P' and h[1] in b'14' and h[2] in b' \t\n\r':
            return 'pbm'
        """PGM (portable graymap)"""
        if len(h) >= 3 and \
                h[0] == b'P' and h[1] in b'25' and h[2] in b' \t\n\r':
            return 'pgm'
        """PPM (portable pixmap)"""
        if len(h) >= 3 and h[0] == b'P' and h[1] in b'36' and h[2] in b' \t\n\r':
            return 'ppm'
        """Sun raster file"""
        if h[:4] == b'\x59\xA6\x6A\x95':
            return 'rast'
        """X bitmap (X10 or X11)"""
        s = b'#define '
        if h[:len(s)] == s:
            return 'xbm'
        return None
