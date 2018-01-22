#!/usr/bin/env python
# -*- coding:utf-8 -*-

# __author__ = 'yaphetsglhf'

from . import api
from flask import request, render_template, jsonify
import json
import logging
import requests
from flask_login import login_required
from config import mongodb_init
from bson import ObjectId
from ..models import FlaskUser


# 调试用的接口
@api.route('/test')
@api.route('/test/<int:test_id>', methods=['GET'])
def get_test_id(test_id=0):

    user = FlaskUser.query.filter_by(id=test_id).first_or_404()

    return {"code": test_id, "user_id": user.id}


@api.route('/mongo')
def get_mongo():
    col = mongodb_init().book_log

    for i in col.find({"_id": ObjectId("587d56a0d165d81490d79a9c")}):
        print i

    print type(col)
    return json.dumps({"code": "success"})