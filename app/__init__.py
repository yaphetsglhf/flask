#!/usr/bin/evn python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from flask import Flask, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_pagedown import PageDown
from flask_restful import Api
import sys
sys.path.append('..')
from config import config
from config import LogConfig
from werkzeug.datastructures import Headers
import logging


# 日志初始化 debug用来调试,info用来输出信息,error记录错误,调试完毕,json里面将debug改为info
LogConfig.log_init()

db = SQLAlchemy()
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
pagedown = PageDown()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
# 设置登录页面的端点
login_manager.login_view = 'auth.login'


class MyResponse(Response):
    # ajax跨域
    def __init__(self, response=None, **kwargs):
        logging.debug(kwargs)
        logging.debug(kwargs.get('headers'))
        headers = kwargs.get('headers')
        origin = ('Access-Control-Allow-Origin', '*')
        methods = ('Access-Control-Allow-Methods', 'HEAD, OPTIONS, GET, POST, DELETE, PUT')

        if headers:
            headers.add_header(*origin)
            headers.add_header(*methods)
        else:
            headers = Headers([origin, methods])

        kwargs['headers'] = headers
        logging.debug(kwargs)
        logging.debug(kwargs.get('headers'))
        logging.debug(type(kwargs.get('headers')))
        super(MyResponse, self).__init__(response, **kwargs)

    @classmethod
    def force_type(cls, rv, environ=None):
        if isinstance(rv, dict):
            rv = jsonify(rv)
        return super(MyResponse, cls).force_type(rv, environ)


class MyFlask(Flask):
    response_class = MyResponse


def create_app(config_name):
    app = MyFlask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app, config_name)   # 继承的静态方法,区别于flask自带init_app方法,用于扩展。作用详见https://segmentfault.com/q/1010000003050323

    db.init_app(app)   # flask自带扩展的方法,不同于上面的init_app()方法
    bootstrap.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    moment.init_app(app)
    pagedown.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    from .api_1_1 import api as api_1_1_blueprint
    app.register_blueprint(api_1_1_blueprint, url_prefix='/api/v1.1')

    return app
