#!/usr/bin/env python
# -*- coding:utf-8 -*-

# __author__ = 'yaphetsglhf'

from . import api
from flask import request, render_template, jsonify


@api.route('/test', methods=['POST'])
def test():
    id = request.form.get('id')
    return {'api': 'Version1.1', 'id': id}