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
from constants import Response, Config
from pretreatment import preprocessing
from config import ModelConfig


class ParamUtils(object):

    @staticmethod
    def filter(param):
        if isinstance(param, list) and len(param) > 0 and isinstance(param[0], bytes):
            return param[0].decode()
        return param


class SignUtils(object):

    @staticmethod
    def md5(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def timestamp():
        return int(time.mktime(datetime.datetime.now().timetuple()))


class PathUtils(object):

    @staticmethod
    def get_file_name(path: str):
        if '/' in path:
            return path.split('/')[-1]
        elif '\\' in path:
            return path.split('\\')[-1]
        else:
            return path


class ImageUtils(object):

    def __init__(self, model: ModelConfig):
        self.model = model

    @staticmethod
    def get_bytes_batch(base64_img):
        response = Response()
        try:
            if isinstance(base64_img, list):
                bytes_batch = [base64.b64decode(i.encode('utf-8')) for i in base64_img if isinstance(i, str)]
                if not bytes_batch:
                    bytes_batch = [base64.b64decode(i) for i in base64_img if isinstance(i, bytes)]
            else:
                bytes_batch = base64.b64decode(base64_img.encode('utf-8')).split(Config.split_flag)
        except binascii.Error:
            return None, response.INVALID_BASE64_STRING
        what_img = [ImageUtils.test_image(i) for i in bytes_batch]
        if None in what_img:
            return None, response.INVALID_IMAGE_FORMAT
        return bytes_batch, response.SUCCESS

    @staticmethod
    def get_image_batch(model: ModelConfig, bytes_batch, color=None):
        # Note that there are two return objects here.
        # 1.image_batch, 2.response

        response = Response()

        hsv_map = {
            "blue": {
                "lower_hsv": np.array([100, 128, 46]),
                "high_hsv": np.array([124, 255, 255])
            },
            "red": {
                "lower_hsv": np.array([0, 128, 46]),
                "high_hsv": np.array([5, 255, 255])
            },
            "yellow": {
                "lower_hsv": np.array([15, 128, 46]),
                "high_hsv": np.array([34, 255, 255])
            },
            "green": {
                "lower_hsv": np.array([35, 128, 46]),
                "high_hsv": np.array([77, 255, 255])
            },
            "black": {
                "lower_hsv": np.array([0, 0, 0]),
                "high_hsv": np.array([180, 255, 46])
            }
        }

        def separate_color(pil_image, color):
            hsv = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_BGR2HSV)
            lower_hsv = hsv_map[color]['lower_hsv']
            high_hsv = hsv_map[color]['high_hsv']
            mask = cv2.inRange(hsv, lowerb=lower_hsv, upperb=high_hsv)
            return mask

        def load_image(image_bytes, color=None):

            if color and color in ['red', 'blue', 'black', 'green', 'yellow']:
                image = np.asarray(bytearray(image_bytes), dtype="uint8")
                image = cv2.imdecode(image, -1)
                image = separate_color(image, color)
            else:
                data_stream = io.BytesIO(image_bytes)
                pil_image = PIL_Image.open(data_stream).convert('RGB')
                image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2GRAY)
            image = preprocessing(image, model.binaryzation, model.smooth, model.blur).astype(np.float32)
            image = cv2.resize(image, (model.resize[0], model.resize[1]))
            image = image.swapaxes(0, 1)
            return image[:, :, np.newaxis] / 255.

        try:
            image_batch = [load_image(i, color=color) for i in bytes_batch]
            return image_batch, response.SUCCESS
        except OSError:
            return None, response.IMAGE_DAMAGE
        except ValueError as _e:
            print(_e)
            return None, response.IMAGE_SIZE_NOT_MATCH_GRAPH

    @staticmethod
    def pil_image(image_bytes):
        data_stream = io.BytesIO(image_bytes)
        pil_image = PIL_Image.open(data_stream).convert('RGB')
        return pil_image

    @staticmethod
    def size_of_image(image_bytes: bytes):
        _null_size = tuple((-1, -1))
        try:
            data_stream = io.BytesIO(image_bytes)
            size = PIL_Image.open(data_stream).size
            return size
        except OSError:
            return _null_size
        except ValueError:
            return _null_size

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
