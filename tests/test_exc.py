#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from werkzeug.security import generate_password_hash, check_password_hash
from Kid17_flask.app.models import IbookOrder
import datetime
import os
import requests
from PIL import Image
from cStringIO import StringIO
import urllib
import logging
import zipfile
import pymongo
from time import ctime


def exc_passwd():
    a = "kobe.com"
    b = generate_password_hash(a)
    print b
    print check_password_hash(b, a)


def exc_return():
    if True:
        try:
            print '1'
            return False
        except:
            print '2'
    print '3'
    return True


class Role(object):

    @staticmethod
    def insert_roles():
        roles = {'User': ('a', 'b'),
                 'Moderator': ('c', 'd'),
                 'Administrator': None
                 }
        for r in roles:
            print r


def net_url():
    try:
        url = "http://resource.kid17.com/xxx.png"
        res = requests.get(url)
        logging.debug("xxxxx")
        if res.status_code == 200:
            with open('/test/222.png', 'wb') as f:
                f.write(res.content)

    except Exception, e:
        logging.debug(">>>>>>Exception: %s" % e)


def mongodb_con():
    client = pymongo.MongoClient("mongodb://106.14.41.71")
    db = client.kid
    db.authenticate("yqzd", "kId17.c0m789")
    # db.authenticate("kid17admin", "Kid17.Com0824")
    col = db.test987

    return col


def threads():
    print ctime()


if __name__ == '__main__':
    col = mongodb_con()
    res = col.find({"web":"www.baidu.com"})
    for i in res:
        print i




