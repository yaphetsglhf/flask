#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views
