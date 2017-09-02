#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from flask import Blueprint
from ..models import Permission

main = Blueprint('main', __name__)


# Permission 类加入模板上下文,上下文处理器能让变量在所有<模板>中全局可访问
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)

from . import views, errors
