#!/usr/bin/env python
# -*- coding:utf-8 -*-

# __author__ = 'yaphetsglhf'

import logging.config
import os
import json
from pymongo import MongoClient
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, Numeric, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# 常量
START_TIME = 1472659200
TERM_TIME = 1486915200
KIND_LIST = (2, 3, 4, 5, 6, 13, 47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 62, 64, 65)
TERM_ID = 4


def mongodb_init():
    client = MongoClient("", 27017)

    db = client.kid

    # 返回bool类型true或者false
    connect_flag = client.kid.authenticate('', '', mechanism='MONGODB-CR')

    if connect_flag:
        # 返回数据库,方便统一管理
        return db
    else:
        return False


class LogConfig(object):
    json_path = os.path.dirname(os.path.abspath(__file__)) + '/logging.json'

    @staticmethod
    def log_init(
            default_path=json_path,
            default_level=logging.INFO,
            env_key='LOG_CFG'):

        path = default_path
        value = os.getenv(env_key, None)

        if value:
            path = value

        if os.path.exists(path):
            with open(path, 'rt') as f:
                cfg = json.load(f)
            logging.config.dictConfig(cfg)
        else:
            logging.basicConfig(level=default_level)

    @staticmethod
    def basic_config():
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class Config(object):
    SECRET_KEY = ''
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MAIL_SERVER = ''
    MAIL_USERNAME = ''
    # 客户端授权密码,区别于邮箱本身密码,需要开启客户端授权功能
    MAIL_PASSWORD = ''
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = ''
    FLASKY_ADMIN = ''
    # 邮件主题的前缀和发件人的地址
    # FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    # FLASKY_MAIL_SENDER = 'Flasky Admin <flasky@example.com>'
    FLASKY_POSTS_PER_PAGE = 20

    # 自己定义的方法,只是没有写具体方法
    @staticmethod
    def init_app(app, config_name):
        logging.debug(config[config_name])


# 正式服
class OfficialConfig(Config):
    SQLALCHEMY_DATABASE_URI = ''


#  测试服
class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = ''


# flask服务器
class FlaskConfig(Config):
    SQLALCHEMY_DATABASE_URI = ''


class LocalhostConfig(Config):
    SQLALCHEMY_DATABASE_URI = ''


config = {'official': OfficialConfig,
          'test': TestingConfig,
          'flasky': FlaskConfig,
          'localhost': LocalhostConfig,
          'default': LocalhostConfig
          }