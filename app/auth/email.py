#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from .. import mail
from flask_mail import Message
from flask import render_template, redirect, url_for, current_app
from threading import Thread


# 异步发送
def send_async_email(myapp, msg):
    with myapp.app_context():
        mail.send(msg)


def send_message(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(subject=subject, recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr



