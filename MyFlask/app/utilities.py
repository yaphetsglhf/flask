#!usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

import sys
import hashlib
import urllib2
import time
import logging
import json
from flask import jsonify
import xlwt

reload(sys)
sys.setdefaultencoding('utf8')


class Message(object):
    def __init__(self, phone, message):
        self.phone = phone
        self.message = message + ''
        self.url = ''
        self.username = 'yqzd'
        self.key = time.strftime('%Y%m%d%H%M%S')
        self.productid = ''

    def md5(self, args):
        m = hashlib.md5()
        m.update(args)
        return m.hexdigest().lower()

    def send_message(self):
        password = self.md5(self.md5('YQZDkid17') + self.key)

        web_url = '%s?username=%s&password=%s&tkey=%s&mobile=%s&content=%s&productid=%s&xh=' % \
                  (self.url, self.username, password, self.key, self.phone, self.message, self.productid)

        try:
            req = urllib2.Request(web_url)
            res = urllib2.urlopen(req)
            m_data = res.read()

            if m_data.split(',')[0] == '1':
                return json.dumps({"code": 0})
            else:
                return json.dumps({"code": 1})
        except Exception, e:
            logging.debug(e)
            return json.dumps({"code": 2})


class GenerateExcel(object):
    # 设置表格样式
    def set_style(self, name, height, bold=False):
        style = xlwt.XFStyle()
        font = xlwt.Font()
        font.name = name
        font.bold = bold
        # font.colour_index = 1
        font.height = height
        style.font = font

        return style

    # 只有一个sheet的excel表 sheets=[sheet_name, raw_data, sheet_data]
    def write_to_excel(self, sheet_list, excel_name, address):
        f = xlwt.Workbook(style_compression=2)
        for sheets in sheet_list:
            sheet = f.add_sheet(sheets[0], cell_overwrite_ok=True)
            # 第一行导航
            for index, item in enumerate(sheets[1]):
                sheet.write(0, index, item, self.set_style('Times New Roman', 220, True))
            for index, item in enumerate(sheets[2]):
                for i, j in enumerate(item):
                    sheet.write(index+1, i, j, self.set_style('Times New Roman', 220, True))
        try:
            f.save(address + excel_name + '.xls')
        except Exception, e:
            logging.debug(">>>>>>Exception: %s" % e)
