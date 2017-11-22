#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from . import main
from .. import db
from flask import render_template, flash, url_for, redirect, request, abort, jsonify, current_app, make_response, session
from ..models import FlaskUser, IbookOrder, Feedback, Guardian, FlaskPost
from config import TERM_TIME, START_TIME, KIND_LIST, TERM_ID
import logging
import json
from ..utilities import Message
from flask_login import login_required
from ..models import FlaskRole
from ..utilities import GenerateExcel
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from flask_login import current_user
from ..models import admin_required, Permission
import datetime


@main.route('/editprofile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.fullname = form.fullname.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data

        db.session.add(current_user)
        db.session.commit()

        flash("Your profile has been updated")

        return redirect(url_for('main.get_user', username=current_user.username))

    # 设置初始值,进入页面默认值
    form.fullname.data = current_user.fullname
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me

    return render_template('main/editprofile.html', form=form)


@main.route('/editprofile/<int:uid>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(uid):
    logging.debug(current_user.is_authenticated)
    user = FlaskUser.query.get_or_404(uid)
    form = EditProfileAdminForm(user=user)

    logging.debug(user)

    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = FlaskRole.query.get(form.role.data)
        user.fullname = form.fullname.data
        user.location = form.location.data
        user.about_me = form.about_me.data

        db.session.add(user)
        db.session.commit()

        flash("Your profile has been updated.")
        return redirect(url_for('main.get_user', username=user.username))

    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.fullname.data = user.fullname
    form.location.data = user.location
    form.about_me.data = user.about_me

    return render_template('main/editprofile.html', form=form, user=user)


# 生成数据库权限
@main.route("/setrole")
@login_required
def set_flaskrole():
    role = FlaskRole()
    role.insert_roles()
    return json.dumps({"code": "success"})


# 插入虚拟数据
@main.route('/datagenerate')
def generate_data():
    FlaskUser.generate_fake()
    FlaskPost.generate_fake()
    return jsonify({"code": "success"})


'''
网站使用uri

'''


@main.route('/', methods=['GET', 'POST'])
def index():
    # x = request.__dict__['headers']
    # print x
    # print type(x)

    # session['author'] = 'yaphetsglhf'
    # logging.debug("session: {}".format(session))
    form = PostForm()

    '''
    current_user 由 Flask-Login 提供,和所有上下文变量一样,也是通过线程内的代理对象实 现。
    这个对象的表现类似用户对象,但实际上却是一个轻度包装,包含真正的用户对象。
    数据库需要真正的用户对象,因此要调用 _get_current_object() 方法

    '''
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        logging.debug(">>>>>writeToDatabase")
        post = FlaskPost(body=form.body.data,
                         author=current_user._get_current_object())
        logging.debug(post)
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    pagination = FlaskPost.query.order_by(
        FlaskPost.create_time.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)

    posts = pagination.items

    # posts = FlaskPost.query.order_by(FlaskPost.create_time.desc()).all()

    return render_template('main/index.html', title='Index', posts=posts, form=form, pagination=pagination)


@main.route('/post/<int:id>')
def post(id):
    post = FlaskPost.query.get_or_404(id)
    return render_template('main/post.html', title='Post', posts=[post])


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = FlaskPost.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash("The post has been updated!")

        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    return render_template('main/edit_post.html', title='Edit', form=form)


@main.route('/user/<username>')
def get_user(username):
    user = FlaskUser.query.filter_by(username=username).first()

    if user is None:
        abort(404)

    # 转化为utc时间,因为moment.js使用utc时间
    user.last_seen = user.last_seen + datetime.timedelta(hours=-8)

    posts = user.posts.order_by(FlaskPost.create_time.desc()).all()

    return render_template('main/user.html', user=user, title='User', posts=posts)


@main.route("/totalstatics", methods=['GET', 'POST'])
def kinder_statics():
    args = request.args if request.method == 'GET' else request.form

    # page = args.get('page', 1)
    page = 1
    download_args = args.get('download_args')

    logging.debug("download_args: %s" % download_args)

    sql_total = u"select k.name as '幼儿园', " \
                "(select count(distinct c.grade_id) from clazz c " \
                u"left join grade d on d.id=c.grade_id " \
                u"where c.kind_id=k.id and d.term_id=:term_id and d.is_del=0 and c.is_del=0) as '年级数', " \
                "(select count(*) from clazz c " \
                u"left join grade d on d.id = c.grade_id " \
                u"where c.kind_id=k.id and d.term_id=:term_id and d.is_del=0 and c.is_del=0) as '班级数', " \
                "(select count(*) from `user` u " \
                "left join clazz c on FIND_IN_SET(u.id,c.user_id) " \
                "left join grade d on d.id=c.grade_id " \
                u"where u.kind_id = k.id and u.is_del=0 and c.is_del=0 and d.is_del=0 and d.term_id=:term_id) as '带班老师数', " \
                "(select count(*) from `user` u " \
                "left join clazz c on FIND_IN_SET(u.id,c.user_id) " \
                "left join grade d on d.id = c.grade_id " \
                u"where u.kind_id = k.id and c.is_del=0 and u.is_del=0 and (u.is_init=1 or u.vertify_code <>'' ) and d.is_del=0 and d.term_id=:term_id) as '激活老师数', " \
                "(select count(*) from guardian g " \
                "left join clazz c on c.id = g.class_id " \
                "left join grade d on d.id = c.grade_id " \
                u"where g.kind_id=k.id and g.is_del=0 and c.is_del=0 and d.is_del=0 and d.term_id=:term_id) as '学生数', " \
                "(select count(*) from guardian g " \
                "left join clazz c on c.id = g.class_id " \
                "left join grade d on d.id = c.grade_id " \
                u"where g.kind_id=k.id and g.is_del=0 and c.is_del=0 and d.is_del=0 and d.term_id=:term_id and g.vertify_code <> '') as '激活学生数' " \
                "from kindergarten k " \
                "where k.id in :kind_list " \
                # "limit :page, 30 "

    inf = db.session.execute(sql_total, {'term_id': TERM_ID, 'kind_list': KIND_LIST}).fetchall()

    logging.debug("sssss: %s", inf)
    if download_args is not None and download_args == "1":
        this_excel = GenerateExcel()
        head_raw = [u'幼儿园', u'年级数', u'班级数', u'带班老师数', u'激活老师数', u'学生数', u'激活学生数']
        this_excel.write_to_excel(sheet_list=((u'幼儿园统计', head_raw, inf),), excel_name='kindergarten', address='/alidata/www/Kid17_flask/excel/')
        # this_excel.write_to_excel(sheet_list=((u'幼儿园统计', head_raw, inf),), excel_name='kindergarten', address='excel/')
        return json.dumps({"code": 1})
    else:
        kind_num = len(KIND_LIST)
        grade_num = reduce(lambda x, y: x+y, [i[1] for i in inf], 0)
        class_num = reduce(lambda x, y: x+y, [i[2] for i in inf])
        teacher_num = reduce(lambda x, y: x+y, [i[3] for i in inf])
        teacher_num_used = reduce(lambda x, y: x+y, [i[4] for i in inf])
        student_num = reduce(lambda x, y: x+y, [i[5] for i in inf])
        student_num_used = reduce(lambda x, y: x+y, [i[6] for i in inf])

        total_static = [kind_num, grade_num, class_num, teacher_num, teacher_num_used, student_num, student_num_used]

        if len(inf) == 0:
            return render_template('empty.html', title='Kindergarten')
        else:
            return render_template('main/totalstatics.html', inf=inf, inf2=total_static, title='Kindergarten', page_num=page)


@main.route("/feedback", methods=['GET', 'POST'])
def get_feedback():
    logging.debug(request.method)

    args = request.args if request.method == 'GET' else request.form
    # page 为unicode类型
    page = args.get('page', 1)
    logging.debug("page: %s" % page)

    sql_feedback = "select f.content, case when SUBSTR(user_id,1,2)='g_' then (select g.child_name " \
                   "from guardian g " \
                   "where f.user_id=CONCAT('g_',g.id)) " \
                   "else (select u.name from user u where f.user_id=CONCAT('t_',u.id)) end as 'name', " \
                   "case when SUBSTR(user_id,1,2)='g_' then (select g.phone from guardian g where f.user_id=CONCAT('g_',g.id)) " \
                   "else (select u.phone from user u where f.user_id=CONCAT('t_',u.id)) end as 'phone', " \
                   u"case when SUBSTR(user_id,1,2)='g_' then '家长' else '老师' end as 'role', FROM_UNIXTIME(f.create_time), " \
                   "f.id as fid, f.if_reply " \
                   "from feedback f " \
                   "where f.create_time > :time " \
                   "order by f.id desc " \
                   "limit :page, 30"

    inf = db.session.execute(sql_feedback, {'time': START_TIME, 'page': 30*(int(page)-1)}).fetchall()

    # 判断是否是最后一页
    if len(inf) == 0:
        logging.debug("null")
        return render_template('empty.html', title='Feedback')
    else:
        return render_template('main/feedback.html', inf=inf, title='Feedback', page_num=page)


@main.route('/fbanswer', methods=['POST'])
def send_fbanswer():
    logging.debug(request.form)
    data = {key: dict(request.form)[key][0] for key in dict(request.form)}

    message = data.get('message')
    phone = data.get('phone')
    if_reply = data.get('if_reply')
    feedback_id = data.get('fid')
    reply_content = data.get('reply_content')

    logging.debug("message: %s, phone: %s, if_reply: %s, feedback_id: %s, reply_content: %s" % (message, phone, if_reply, feedback_id, reply_content))

    if if_reply is not None and if_reply == "1":
        logging.debug("111")
        Feedback.query.filter_by(id=feedback_id).update({"if_reply": 1, "reply_content": reply_content})
        db.session.commit()

        return json.dumps({"code": "success"})
    else:
        logging.debug("222")
        m = Message(phone, message)

        logging.debug("code: %s" % json.loads(m.send_message()).get('code'))

        if json.loads(m.send_message()).get('code') == 0:
            logging.debug("333")
            return json.dumps({"code": 0})
        else:
            logging.debug("444")
            return json.dumps({"code": 1})


@main.route("/ibooknote", methods=['GET', 'POST'])
def get_ibooknote():
    args = request.args if request.method == 'GET' else request.form
    page = args.get('page', 1)

    logging.debug('page: %s' % page)

    sql_ibooknote = "select g.child_name, g.phone, g.role, i.note, FROM_UNIXTIME(i.create_time) " \
                    "from ibook_order i " \
                    "left join guardian g on g.id = i.uid " \
                    "where i.term_id = :term_id and i.is_del=0 and i.is_draft=0 " \
                    "order by i.id desc " \
                    "limit :page, 30"

    # inf = db.session.query(Guardian.child_name, Guardian.phone, Guardian.role, IbookOrder.note, IbookOrder.create_time).filter(Guardian.id == IbookOrder.uid, IbookOrder.is_del == 0).order_by(IbookOrder.id.desc()).all()

    inf = db.session.execute(sql_ibooknote, {'term_id': TERM_ID, 'page': 30 * (int(page) - 1)}).fetchall()

    # logging.debug("data: %s" % inf)

    if len(inf) == 0:
        logging.debug("null")
        return render_template('empty.html', title='Ibooknote')
    else:
        return render_template('main/ibooknote.html', inf=inf, title='Ibooknote', page_num=page)
