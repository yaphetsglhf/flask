#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from .. import db
from . import auth
from flask import render_template, flash, url_for, redirect, request
from flask_login import login_required, login_user, logout_user
from ..models import FlaskUser
from .forms import LoginForm, RegistrationForm
from .email import send_message
from flask_login import current_user
import logging


# note: current_user 可以使用所有FlaskUser中的方法。这个是注册一个函数,不同于修饰器,如login_required;
# login_required函数应该在此处使用,避免每次都要写在路由函数前面
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))


# @auth.before_app_request
# def before_request():
#     # 第三个保证: 待验证的用户不会重定向(不在认证蓝本中)  is_authenticated()表示登录了。 static请求css, js要排除
#     if current_user.is_authenticated and not current_user.confirmed and request.endpoint[:5] != 'auth.' and request.endpoint != 'static':
#         return redirect(url_for('auth.unconfirmed'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = FlaskUser.query.filter_by(email=form.email.data).first()

        logging.debug(user)

        # 防止数据库password_hash为空报错
        try:
            if user is not None and user.verify_password(form.password.data) and user.is_del == 0:

                logging.debug('1')

                login_user(user, form.remember_me.data)
                return redirect(url_for('main.index'))
            flash('Invalid Credentials')
        except AttributeError, e:
            logging.info(e)
    # 表示get类型
    return render_template('auth/login.html', form=form, title='Login')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout successfully.")

    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # 验证空字段方法写在form类里面
        user = FlaskUser(email=form.email.data,
                         username=form.username.data,
                         password=form.password.data)

        db.session.add(user)
        db.session.commit()

        token = user.generate_confirmation_token()
        send_message(user.email, subject='Confirm your account', template='auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')

        return redirect(url_for('main.index'))

    return render_template('auth/register.html', form=form, title='Register')


# 重新发送邮件的链接地址,单独写因为之前发送邮件绑定在注册页面
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_message(current_user.email, subject='Confirm your account', template='auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')

    return redirect(url_for('main.index'))


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    logging.debug("try to confirm")
    # 已经认证
    if current_user.confirmed:
        logging.debug('xxx')
        return redirect(url_for('main.index'))
    # 此confirm是FlaskUser里面的方法,current_user完全在模型里面认证
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')

    return redirect(url_for('main.index'))


@auth.route('/unconfirmed')
def unconfirmed():
    # 普通用户返回false, is_active, is_anonymous, and is_authenticated are all properties as of Flask-Login 0.3
    if current_user.is_anonymous:
        return redirect(url_for('main.index'))

    return render_template('auth/email/unconfirmed.html', title='Confirm your account')



