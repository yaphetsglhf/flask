#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from flask import render_template, make_response, jsonify
from . import main


@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', title="404 error"), 404
    # return make_response(jsonify({"error": "not found"}), 404)


@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', title="500 error"), 500


@main.app_errorhandler(403)
def forbidden_error(e):
    return render_template('errors/403.html', title="403 error"), 403
