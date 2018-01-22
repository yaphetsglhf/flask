#!usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, Numeric, String, Text, text, Boolean
from . import db, login_manager
from flask_login import UserMixin, AnonymousUserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, abort
from functools import wraps
import datetime
import logging


# 加载用户的回调函数
@login_manager.user_loader
def load_user(user_id):
    return FlaskUser.query.get(int(user_id))


class FlaskUser(UserMixin, db.Model):
    __tablename__ = 'flaskuser'

    id = Column(Integer, primary_key=True)
    email = Column(String(64))
    username = Column(String(32))
    password_hash = Column(String(128))
    role_id = Column(Integer, db.ForeignKey('flaskrole.id'))
    confirmed = Column(Boolean, default=False)
    is_del = Column(Boolean, default=False)
    location = Column(String(128))
    about_me = Column(Text)
    last_seen = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    fullname = Column(String(32))
    member_since = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    posts = db.relationship('FlaskPost', backref='author', lazy='dynamic')

    # 注册时调用初始化方法,赋予用户角色。主要分管理员和普通用户
    def __init__(self, **kwargs):
        # 调用父类的方法
        super(FlaskUser, self).__init__(**kwargs)

        # flaskrole反向引用
        if self.flaskrole is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.flaskrole = FlaskRole.query.filter_by(permission=0xff).first()
            else:
                self.flaskrole = FlaskRole.query.filter_by(default=True).first()

    # 构造虚假的数据
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            user = FlaskUser(email=forgery_py.internet.email_address(),
                             username=forgery_py.internet.user_name(True),
                             password_hash=forgery_py.lorem_ipsum.word(),
                             confirmed=True,
                             fullname=forgery_py.name.full_name(),
                             location=forgery_py.lorem_ipsum.sentence(),
                             member_since=forgery_py.date.date(True)
                             )
            db.session.add(user)

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def ping(self):
        self.last_seen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.session.add(self)
        db.session.commit()

    def can(self, permission):
        return (self.flaskrole is not None) and ((self.flaskrole.permission & permission) == permission)

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    # 将方法变为属性 models方法中提交password,触发这个属性方法
    @password.setter
    def password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def verify_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    def generate_confirmation_token(self):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=3600)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)

            logging.debug(data)

        except:
            return False

        if data.get('confirm') != self.id:
            logging.debug(data.get('confirm'))
            logging.debug(self.id)

            return False

        self.confirmed = True
        # 待审核去掉是否也作用
        # db.session.add(self)
        db.session.commit()

        return True

    def __repr__(self):
        return '<FlaskUser (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' % \
               (self.id, self.email, self.username, self.password_hash, self.role_id, self.confirmed, self.is_del,
                self.location, self.about_me, self.last_seen, self.member_since, self.fullname)


# 将其设为用户未登录时 current_user 的值
class AnonymousUser(AnonymousUserMixin):
    def can(self, permission):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


# 检查用户权限。自定义修饰器。为下面的方法服务
# @permission_required(permission) 加在方法前,那么那个方法就是f,即在运行方法钱先执行修饰器方法, permission是参数项。
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMINISTER)(f)


class FlaskRole(db.Model):
    __tablename__ = 'flaskrole'

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    default = Column(Integer, server_default=text("'0'"))
    permission = Column(Integer)
    users = db.relationship('FlaskUser', backref='flaskrole', lazy='dynamic')

    # 创建role对象
    @staticmethod
    def insert_roles():
        roles = {'FlaskUser': (Permission.FOLLOW |
                               Permission.COMMENT |
                               Permission.WRITE_ARTICLES, True),  # True 表明默认用户的权限(数据库default)
                 'Moderator': (Permission.FOLLOW |
                               Permission.COMMENT |
                               Permission.WRITE_ARTICLES |
                               Permission.MODERATE_COMMENTS, False),
                 'Administrator': (0xff, False)
                 }

        for r in roles:
            # 检索数据库名字为r的role。是否存在
            role = FlaskRole.query.filter_by(name=r).first()
            # 不存在该角色
            if role is None:
                role = FlaskRole(name=r)
            role.permission = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)

        db.session.commit()

    def __repr__(self):
        return '<FlaskRole (%r, %r, %r, %r, %r)>' % (self.id, self.name, self.default, self.permission, self.user_id)


# 操作的权限
class Permission(object):
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class FlaskPost(db.Model):
    __tablename__ = 'flaskpost'

    id = Column(Integer, primary_key=True)
    body = Column(Text)
    create_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    author_id = Column(Integer, db.ForeignKey('flaskuser.id'))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        user_count = FlaskUser.query.count()

        seed()
        for i in range(count):
            u = FlaskUser.query.offset(randint(0, user_count-1)).first()
            p = FlaskPost(body=forgery_py.lorem_ipsum.sentences(randint(0, 3)),
                          create_time=forgery_py.date.date(True),
                          author=u
                          )
            db.session.add(p)
            db.session.commit()

    def __repr__(self):
        return '<FlaskPost (%r, %r, %r, %r)>' % \
               (self.id, self.body, self.create_time, self.author_id)


# 公司数据库模型*********************************************************************************


class Activity(db.Model):
    __tablename__ = 'activity'

    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    tag = Column(Text)
    content = Column(String(255))
    text = Column(String(255))
    class_id = Column(Integer)
    create_id = Column(Integer)
    subject_id = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    kind_id = Column(Integer)
    ins_id = Column(Integer)

    def __repr__(self):
        return '<Activity (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' % \
               (self.id, self.title, self.tag, self.content, self.text, self.class_id, self.create_id, self.subject_id,
                self.is_del, self.create_time, self.kind_id, self.ins_id)


class ActivityPic(db.Model):
    __tablename__ = 'activity_pic'

    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    title = Column(String(255))
    user_id = Column(Integer)
    create_time = Column(Integer)
    tag = Column(String(255))
    is_del = Column(Integer)


class Addres(db.Model):
    __tablename__ = 'address'

    id = Column(Integer, primary_key=True)
    address = Column(String(255))
    areaid = Column(Integer)
    phone = Column(String(30))
    name = Column(String(30))
    create_time = Column(Integer)
    is_del = Column(Integer)
    user_id = Column(Integer)
    weight = Column(Integer)


class AppArticle(db.Model):
    __tablename__ = 'app_article'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    url = Column(String(255))
    views = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    is_send = Column(Integer)
    thumb = Column(String(255))


class AppArticleLast(db.Model):
    __tablename__ = 'app_article_last'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    last_id = Column(Integer)
    create_time = Column(Integer)


class AppArticleRead(db.Model):
    __tablename__ = 'app_article_read'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer)
    create_time = Column(Integer)
    uid = Column(Integer)


class AppMessage(db.Model):
    __tablename__ = 'app_message'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(Text)
    is_del = Column(Integer)
    create_time = Column(Integer)


class Appericate(db.Model):
    __tablename__ = 'appericate'

    id = Column(Integer, primary_key=True)
    guardian_id = Column(Integer)
    is_del = Column(Integer)
    has_read = Column(Integer)
    subject_id = Column(Integer)
    data = Column(String(255))


class Area(db.Model):
    __tablename__ = 'area'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)
    sort = Column(Integer, nullable=False)


class Article(db.Model):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    cate_id = Column(Integer)
    title = Column(String(255))
    content = Column(String)
    create_id = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    moudle = Column(String(40))
    act = Column(String(40))


class ArticleCate(db.Model):
    __tablename__ = 'article_cate'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    is_del = Column(Integer)
    parent = Column(Integer)
    level = Column(Integer)


class ArticleCopy(db.Model):
    __tablename__ = 'article_copy'

    id = Column(Integer, primary_key=True)
    cate_id = Column(Integer)
    title = Column(String(255))
    content = Column(String)
    create_id = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    moudle = Column(String(40))
    act = Column(String(40))


class AssDraft(db.Model):
    __tablename__ = 'ass_draft'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer)
    class_id = Column(Integer)
    content = Column(String)
    is_del = Column(Integer)
    star = Column(String)


class Book(db.Model):
    __tablename__ = 'book'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    tid = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    last_edit_time = Column(Integer)
    term_id = Column(Integer)


class BookOrder(db.Model):
    __tablename__ = 'book_order'

    id = Column(Integer, primary_key=True)
    bid = Column(Integer)
    create_time = Column(Integer)
    uid = Column(Integer)
    status = Column(Integer)
    type = Column(String(2))
    tb_order = Column(BigInteger)
    is_del = Column(Integer)
    en = Column(String(32))
    has_out = Column(Integer)
    download = Column(String(100))


class BookPick(db.Model):
    __tablename__ = 'book_pick'

    id = Column(Integer, primary_key=True)
    sid = Column(Integer)
    type = Column(String(2))
    create_time = Column(Integer)


class BookPrint(db.Model):
    __tablename__ = 'book_print'

    id = Column(Integer, primary_key=True)
    oid = Column(Integer)
    html = Column(String(255))
    pic = Column(String(50))


class BookPrintimage(db.Model):
    __tablename__ = 'book_printimages'

    id = Column(Integer, primary_key=True)
    oss = Column(String(255))
    local = Column(String(255))


class BookSheet(db.Model):
    __tablename__ = 'book_sheet'

    id = Column(Integer, primary_key=True)
    bid = Column(Integer)
    uid = Column(Integer)
    pid = Column(String(23), index=True)
    side = Column(Integer)
    span = Column(Integer)
    is_self = Column(Integer)
    thumb_count = Column(Integer)


class BookTemplate(db.Model):
    __tablename__ = 'book_template'

    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    en = Column(String(50))
    create_time = Column(Integer)
    is_del = Column(Integer)
    s_page = Column(Integer)
    h_page = Column(Integer)
    a_page = Column(Integer)
    s_price = Column(Integer)
    h_price = Column(Integer)
    e_price = Column(Integer)
    cover = Column(String(255))


class Cartoon(db.Model):
    __tablename__ = 'cartoon'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    term_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)
    tid = Column(Integer)
    look_time = Column(Integer)
    last_edit_time = Column(Integer)
    star = Column(Integer)
    pingjia = Column(String(255))
    like = Column(Integer, nullable=False)
    text = Column(String(255))


class CartoonElement(db.Model):
    __tablename__ = 'cartoon_element'

    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    type = Column(Integer)
    num = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    data = Column(String(500))


class CartoonIntro(db.Model):
    __tablename__ = 'cartoon_intro'

    id = Column(Integer, primary_key=True)
    aid = Column(Integer)
    gender = Column(Integer)
    name = Column(String(100))
    kind = Column(String(100))
    clazz = Column(String(100))
    thumb1 = Column(String(100))
    thumb2 = Column(String(100))
    thumb3 = Column(String(100))
    thumb4 = Column(String(100))
    fav = Column(String(500))


class CartoonNote(db.Model):
    __tablename__ = 'cartoon_note'

    id = Column(Integer, primary_key=True)
    aid = Column(Integer)
    voice = Column(String(255))
    text = Column(String(1000))


class CartoonOrder(db.Model):
    __tablename__ = 'cartoon_order'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    tb_order = Column(String(32))
    create_time = Column(Integer)
    is_del = Column(Integer)
    status = Column(Integer)
    tid = Column(Integer)
    video_url = Column(String(255))


class CartoonPhoto(db.Model):
    __tablename__ = 'cartoon_photos'

    id = Column(Integer, primary_key=True)
    aid = Column(Integer)
    scene = Column(String(10))
    objects = Column(String(1000))
    text = Column(String(255))


class CartoonScene(db.Model):
    __tablename__ = 'cartoon_scene'

    id = Column(Integer, primary_key=True)
    tid = Column(Integer)
    type = Column(Integer)
    en = Column(String(50))
    name = Column(String(50))
    is_del = Column(Integer)
    create_time = Column(Integer)
    order = Column(Integer)
    min = Column(Integer)
    max = Column(Integer)
    html = Column(String(255))
    pic = Column(String(255))


class CartoonSheet(db.Model):
    __tablename__ = 'cartoon_sheet'

    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    eid = Column(Integer)
    photos = Column(String(2000))
    text = Column(String)
    weibo_id = Column(String(200))


class CartoonTemplate(db.Model):
    __tablename__ = 'cartoon_template'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    is_del = Column(Integer)
    create_time = Column(Integer)
    en = Column(String(50))
    num_1 = Column(Integer)
    num_2 = Column(Integer)
    num_3 = Column(Integer)
    num_4 = Column(Integer)
    num_5 = Column(Integer)
    num_6 = Column(Integer)
    num_7 = Column(Integer)


class CartoonUnpick(db.Model):
    __tablename__ = 'cartoon_unpick'

    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    pid = Column(String(5000))


class CartoonUnpickAudio(db.Model):
    __tablename__ = 'cartoon_unpick_audio'

    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    aid = Column(String(1000))


class CartoonUpickNote(db.Model):
    __tablename__ = 'cartoon_upick_note'

    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    nid = Column(String(1000))


class CartoonVoice(db.Model):
    __tablename__ = 'cartoon_voice'

    id = Column(Integer, primary_key=True)
    aid = Column(Integer)
    voices = Column(String(500))


class ClassComment(db.Model):
    __tablename__ = 'class_comment'

    id = Column(Integer, primary_key=True)
    class_id = Column(Integer)
    subject_id = Column(Integer)
    stus = Column(Integer)
    picks = Column(Integer)
    ignore_id = Column(String(255))


class Clazz(db.Model):
    __tablename__ = 'clazz'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    name = Column(String(30))
    tag = Column(String(255))
    create_time = Column(Integer)
    is_del = Column(Integer)
    kind_id = Column(Integer, nullable=False)
    grade_id = Column(Integer)
    stus = Column(Integer)
    activitys = Column(Integer)
    tasks = Column(Integer)
    thumb = Column(String(255))

    def __repr__(self):
        return '<Clazz (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' % \
               (self.id, self.user_id, self.name, self.tag, self.create_time, self.is_del, self.kind_id, self.grade_id,
                self.stus, self.activitys, self.tasks, self.thumb)


class Comment(db.Model):
    __tablename__ = 'comment'
    __table_args__ = (
        Index('cid', 'uid', 'to'),
    )

    id = Column(Integer, primary_key=True)
    content = Column(String(255))
    create_time = Column(Integer)
    reply_id = Column(Integer)
    is_del = Column(Integer)
    weibo_id = Column(Integer)
    uid = Column(String(20))
    has_read = Column(Integer)
    to = Column(String(20))

    def __repr__(self):
        return '<Comment (%r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.content, self.create_time, self.reply_id, self.is_del, self.weibo_id, self.uid,
                  self.has_read, self.to)


class DebugLog(db.Model):
    __tablename__ = 'debug_log'

    id = Column(Integer, primary_key=True)
    content = Column(String(255))


class Device(db.Model):
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True)
    device_code = Column(String(255))
    stystem = Column(String(255))
    version = Column(String(255))
    dpi = Column(String(30))
    create_time = Column(Integer)


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(11))
    content = Column(Text)
    create_time = Column(Integer)
    is_del = Column(Integer)
    reply_id = Column(Integer)
    reply_name = Column(String(30))
    reply_time = Column(Integer)
    if_reply = Column(Integer)
    reply_content = Column(Text)

    def __repr__(self):
        return '<Feedback (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.user_id, self.content, self.create_time, self.is_del, self.reply_id, self.reply_name,
                  self.reply_time, self.if_reply, self.reply_content)


class FinishTask(db.Model):
    __tablename__ = 'finish_task'

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer)
    task_name = Column(String(1000, u'utf8mb4_unicode_ci'))
    create_time = Column(Integer)
    term_id = Column(Integer)
    class_id = Column(Integer)
    guardian_id = Column(Integer)


class FormRule(db.Model):
    __tablename__ = 'form_rule'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    mode_id = Column(Integer)
    min = Column(Integer)
    max = Column(Integer)
    name = Column(String(255))
    norule = Column(Integer)


class GlobalConfig(db.Model):
    __tablename__ = 'global_config'

    id = Column(Integer, primary_key=True)
    type = Column(String(20))
    value = Column(String)
    create_time = Column(Integer)
    create_id = Column(Integer)
    is_start = Column(Integer)


class Good(db.Model):
    __tablename__ = 'goods'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(String)
    create_time = Column(Integer)
    price = Column(Numeric(20, 0))
    status = Column(Integer)
    is_del = Column(Integer)
    thumbs = Column(Text)
    weight = Column(Integer)
    thumb = Column(String(255))
    create_id = Column(Integer)


class Grade(db.Model):
    __tablename__ = 'grade'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    name = Column(String(30))
    user_ids = Column(Text)
    kind_id = Column(Integer)
    create_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)
    grade = Column(Integer)
    term_id = Column(Integer)

    def __repr__(self):
        return '<Grade (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.tag, self.name, self.user_ids, self.kind_id, self.create_id, self.create_time, self.is_del, self.grade, self.term_id)


class GradeHistory(db.Model):
    __tablename__ = 'grade_history'

    id = Column(Integer, primary_key=True)
    grade_id = Column(Integer)
    grade = Column(Integer)
    kind_id = Column(Integer)
    term_id = Column(Integer)
    name = Column(String(20))


class GradeTeacher(db.Model):
    __tablename__ = 'grade_teacher'

    id = Column(Integer, primary_key=True)
    userid = Column(Integer)
    grade_id = Column(Integer)
    is_master = Column(Integer)

    def __repr__(self):
        return '<GradeTeacher (%r, %r, %r, %r)>' % (self.id, self.userid, self.grade_id, self.is_master)


class Guardian(db.Model):
    __tablename__ = 'guardian'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    child_name = Column(String(20))
    role = Column(String(20))
    phone = Column(String(20))
    password = Column(String(20))
    class_id = Column(Integer)
    kind_id = Column(Integer)
    create_time = Column(Integer)
    token = Column(String(100))
    vertify_code = Column(String(20))
    deviceid = Column(String(100))
    is_froze = Column(Integer)
    is_del = Column(Integer)
    is_init = Column(Integer)
    thumb = Column(String(100))
    ismain = Column(Integer)
    lastlogin = Column(Integer)
    gender = Column(Integer)
    birthday = Column(Integer)
    mythumb = Column(String(100))
    belong = Column(Integer)
    number = Column(String(10))
    note = Column(String(1000))
    child_py = Column(String(2))
    visits = Column(Integer)
    fav = Column(String(1000))
    htoken = Column(String(50))
    growgrade = Column(String(10))

    def __repr__(self):
        return '<User (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.name, self.child_name, self.role, self.phone, self.password, self.class_id, self.kind_id,
                  self.create_time, self.token, self.vertify_code, self.deviceid, self.is_froze, self.is_del, self.is_init, self.thumb,
                  self.ismain, self.lastlogin,
                  self.gender, self.birthday, self.mythumb, self.belong, self.number, self.note, self.child_py,
                  self.visits, self.fav, self.htoken)


class GuardianLog(db.Model):
    __tablename__ = 'guardian_log'

    id = Column(Integer, primary_key=True)
    ip = Column(String(20))
    create_time = Column(Integer)
    getdata = Column(String(255))
    postdata = Column(Text)
    guardian_id = Column(Integer, index=True)
    controller = Column(String(100))
    action = Column(String(100), index=True)

    def __repr__(self):
        return '<GuardianLog (%r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.ip, self.create_time, self.getdata, self.postdata, self.guardian_id, self.controller,
                  self.action)


class GuardianTask(db.Model):
    __tablename__ = 'guardian_task'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer)
    guardian_id = Column(Integer)
    status = Column(Integer)

    def __repr__(self):
        return '<GuardianTask (%r, %r, %r, %r)>' % (self.id, self.activity_id, self.guardian_id, self.status)


class Healthy(db.Model):
    __tablename__ = 'healthy'

    id = Column(Integer, primary_key=True)
    guardian_id = Column(Integer)
    has_read = Column(Integer)
    is_del = Column(Integer)
    month = Column(Integer)
    class_id = Column(Integer)
    term_id = Column(Integer)
    create_time = Column(Integer)
    create_id = Column(String(20))
    tall = Column(Integer)
    weigh = Column(Integer)
    leftvision = Column(String(10))
    rightvision = Column(String(10))
    weibo_id = Column(Integer)


class HistoryKind(db.Model):
    __tablename__ = 'history_kind'

    id = Column(Integer, primary_key=True)
    kind_id = Column(Integer, nullable=False)
    term_id = Column(Integer)


class IgnoreAct(db.Model):
    __tablename__ = 'ignore_act'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer)
    uid = Column(Integer)
    class_id = Column(Integer)
    create_time = Column(Integer)

    def __repr__(self):
        return '<IgnoreAct (%r, %r, %r, %r, %r)>' % \
               (self.id, self.activity_id, self.uid, self.class_id, self.create_time)


class IgnoreTask(db.Model):
    __tablename__ = 'ignore_task'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    uid = Column(Integer)
    class_id = Column(Integer)
    create_time = Column(Integer)

    def __repr__(self):
        return '<IgnoreTask (%r, %r, %r, %r, %r)>' % (self.id, self.task_id, self.uid, self.class_id, self.create_time)


class Inspiration(db.Model):
    __tablename__ = 'inspiration'

    id = Column(Integer, primary_key=True)
    type = Column(Integer)
    title = Column(String(255))
    content = Column(String)
    order = Column(Integer)
    starttime = Column(Integer)
    endtime = Column(Integer)
    is_del = Column(Integer)
    create_time = Column(Integer)
    short_title = Column(String(50))
    tag = Column(String(50))
    thumbs = Column(String(1000))
    thumb = Column(String(200))
    task_type = Column(Integer)


class Jpush(db.Model):
    __tablename__ = 'jpush'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    create_time = Column(Integer)
    weibo_id = Column(Integer)
    can_push = Column(Integer)
    content = Column(Text)

    def __repr__(self):
        return '<Jpush (%r, %r, %r, %r, %r, %r)>' % \
               (self.id, self.uid, self.create_time, self.weibo_id, self.can_push, self.content)


class Kindergarten(db.Model):
    __tablename__ = 'kindergarten'

    id = Column(Integer, primary_key=True)
    master_id = Column(Integer)
    name = Column(String(100))
    content = Column(Text)
    logo = Column(String(255))
    address = Column(String(255))
    lng = Column(Numeric(10, 0))
    lat = Column(Numeric(10, 0))
    thumbs = Column(Text)
    is_del = Column(Integer)
    create_time = Column(Integer)
    area_id = Column(Integer)
    is_froze = Column(Integer)
    old_master_id = Column(Integer)
    weburl = Column(String(255))
    email = Column(String(255))
    tel = Column(String(30))
    term_id = Column(Integer)
    stu_num = Column(String(2))

    def __repr__(self):
        return '<Kindergarten (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.master_id, self.name, self.content, self.logo, self.address, self.lng, self.lat,
                  self.thumbs, self.is_del, self.create_time, self.area_id, self.is_froze, self.old_master_id,
                  self.weburl, self.email, self.tel, self.term_id, self.stu_num)


class Language(db.Model):
    __tablename__ = 'language'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    value = Column(String(255))
    mode_id = Column(Integer)
    name = Column(String(255))


class LastCircle(db.Model):
    __tablename__ = 'last_circle'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    last_read_id = Column(Integer)


class LastMylist(db.Model):
    __tablename__ = 'last_mylist'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    last_read_id = Column(Integer)


class Like(db.Model):
    __tablename__ = 'like'
    __table_args__ = (
        Index('cid', 'uid', 'to'),
    )

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer)
    is_del = Column(Integer)
    uid = Column(String(20))
    create_time = Column(Integer)
    to = Column(String(20))
    has_read = Column(Integer)

    def __repr__(self):
        return '<Like (%r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.weibo_id, self.is_del, self.uid, self.create_time, self.to, self.has_read)


class Log(db.Model):
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    type = Column(String(255))
    content = Column(Text)
    create_time = Column(Integer)


class LogHotCount(db.Model):
    __tablename__ = 'log_hot_count'

    id = Column(Integer, primary_key=True)
    type = Column(String(20))
    count = Column(Integer)
    date = Column(String(20))
    kind_id = Column(Integer)
    class_id = Column(Integer)


class LogInstallCount(db.Model):
    __tablename__ = 'log_install_count'

    id = Column(Integer, primary_key=True)
    year = Column(Integer)
    month = Column(String(2))
    day = Column(String(2))
    count = Column(Integer)
    date = Column(String(30))


class ManageMode(db.Model):
    __tablename__ = 'manage_mode'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    tag = Column(String(255))
    is_del = Column(Integer)


class Message(db.Model):
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    kind_id = Column(Integer)
    grade_id = Column(Integer)
    class_id = Column(Integer)
    content = Column(String(255))
    create_time = Column(Integer)
    type = Column(Integer)
    utype = Column(Integer)
    is_del = Column(Integer)

    def __repr__(self):
        return '<Message (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.uid, self.kind_id, self.grade_id, self.class_id, self.content, self.create_time,
                  self.type, self.utype, self.is_del)


class MessageRead(db.Model):
    __tablename__ = 'message_read'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer)
    create_time = Column(Integer)

    def __repr__(self):
        return '<MessageRead (%r, %r, %r)>' % (self.id, self.message_id, self.create_time)


class MyMode(db.Model):
    __tablename__ = 'my_mode'

    id = Column(Integer, primary_key=True)
    tag = Column(String(255))
    name = Column(String(255))


class Order(db.Model):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    goods_id = Column(Integer)
    price = Column(String(255))
    pay_type = Column(String(30))
    guardian_id = Column(Integer)
    address_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)


class Photo(db.Model):
    __tablename__ = 'photo'

    id = Column(Integer, primary_key=True)
    object = Column(String(255))
    create_id = Column(String(100), index=True)
    create_time = Column(Integer)
    is_del = Column(Integer)
    stu_ids = Column(String(1000))
    text = Column(Text)
    weibo_id = Column(Integer, index=True)
    rs = Column(Integer)
    class_id = Column(Integer)
    stus = Column(String(255))
    stu_count = Column(Integer)
    local = Column(String(255))
    kind_id = Column(Integer)
    local_url = Column(String(255))

    def __repr__(self):
        return '<Photo (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.object, self.create_id, self.create_time, self.is_del, self.stu_ids, self.text,
                  self.weibo_id, self.rs, self.class_id, self.stus, self.stu_count, self.local, self.kind_id,
                  self.local_url)


class Pic(db.Model):
    __tablename__ = 'pic'

    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    type = Column(String(255))
    create_time = Column(Integer)

    def __repr__(self):
        return '<Pic (%r, %r, %r, %r)>' % (self.id, self.url, self.type, self.create_time)


class Role(db.Model):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    is_del = Column(Integer)

    def __repr__(self):
        return '<Role (%r, %r, %r)>' % (self.id, self.name, self.is_del)


class Sm(db.Model):
    __tablename__ = 'sms'

    id = Column(Integer, primary_key=True)
    msg = Column(String(255))
    phone = Column(String(22))
    create_time = Column(Integer)
    is_del = Column(Integer)


class StarField(db.Model):
    __tablename__ = 'star_fields'

    id = Column(Integer, primary_key=True)
    kind_id = Column(Integer)
    name = Column(String(255, u'utf8mb4_unicode_ci'))
    create_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)


class StuAudio(db.Model):
    __tablename__ = 'stu_audio'

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer)
    uid = Column(Integer)
    audio = Column(String(255))
    create_time = Column(Integer)


class StuComment(db.Model):
    __tablename__ = 'stu_comment'

    id = Column(Integer, primary_key=True)
    create_time = Column(Integer)
    is_del = Column(Integer)
    content = Column(String(1000))
    create_id = Column(String(20))
    weibo_id = Column(Integer)
    stu_id = Column(Integer)


class StuCommentReply(db.Model):
    __tablename__ = 'stu_comment_reply'

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer)
    create_id = Column(String(20))
    content = Column(String(1000))
    create_time = Column(Integer)
    is_del = Column(Integer)
    weibo_id = Column(Integer)


class StuPage(db.Model):
    __tablename__ = 'stu_pages'

    id = Column(Integer, primary_key=True)
    thumb_count = Column(Integer)
    thumbs = Column(String(3000))
    create_time = Column(Integer)
    text = Column(String(2000))
    audio = Column(String(255))
    uid = Column(Integer)
    weibo_id = Column(Integer)


class StuPhoto(db.Model):
    __tablename__ = 'stu_photos'

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer)
    weight = Column(Integer)
    stus = Column(Integer)
    stu_ids = Column(String(255))
    create_time = Column(Integer)
    uid = Column(Integer)
    object = Column(String(255))


class StuStar(db.Model):
    __tablename__ = 'stu_star'

    id = Column(Integer, primary_key=True, nullable=False)
    stu_id = Column(Integer, primary_key=True, nullable=False)
    mod_id = Column(Integer, primary_key=True, nullable=False)
    item_id = Column(Integer, nullable=False)
    star = Column(Integer, nullable=False)
    weibo_id = Column(Integer)


class Subject(db.Model):
    __tablename__ = 'subject'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    tag = Column(Text)
    grade_id = Column(Integer)
    kind_id = Column(Integer)
    content = Column(String(255))
    is_del = Column(Integer)
    create_id = Column(Integer)
    create_time = Column(Integer)
    start_time = Column(Integer)
    end_time = Column(Integer)
    range = Column(String(40))
    items = Column(Text)
    is_start = Column(Integer)
    has_start = Column(Integer)
    has_comment = Column(Integer)
    item_type = Column(String(255))
    term_id = Column(Integer)
    class_id = Column(Integer)
    ins_id = Column(Integer)

    def __repr__(self):
        return '<Subject (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.name, self.tag, self.grade_id, self.kind_id, self.content, self.is_del, self.create_id,
                  self.create_time, self.start_time, self.end_time, self.range, self.items, self.is_start,
                  self.has_start, self.has_comment, self.item_type, self.term_id, self.class_id, self.ins_id)


class SubjectItem(db.Model):
    __tablename__ = 'subject_item'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer)
    term_id = Column(Integer)
    class_id = Column(Integer)
    type = Column(Integer)
    title = Column(String(255))
    is_del = Column(Integer)

    def __repr__(self):
        return '<SubjectItem (%r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.subject_id, self.term_id, self.class_id, self.type, self.title, self.is_del)


class SysAdmin(db.Model):
    __tablename__ = 'sys_admin'

    id = Column(Integer, primary_key=True)
    user = Column(String(30))
    password = Column(String(100))
    is_create = Column(Integer)
    username = Column(String(30))
    create_time = Column(Integer)


class SysLog(db.Model):
    __tablename__ = 'sys_log'

    id = Column(Integer, primary_key=True)
    info = Column(Text)


class SysMessage(db.Model):
    __tablename__ = 'sys_message'

    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    content = Column(Text)
    create_time = Column(Integer)
    to_userid = Column(Integer)
    is_del = Column(Integer)


class Tag(db.Model):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True)
    type = Column(String(30))
    value = Column(Text)
    type_name = Column(String(30))


class Target(db.Model):
    __tablename__ = 'target'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer)
    name = Column(String(255))
    content = Column(Text)
    thumbs = Column(Text)
    pics = Column(Text)
    kind_id = Column(Integer)
    grade_id = Column(Integer)
    create_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)
    status = Column(Integer)
    weibo_id = Column(Integer)
    task_id = Column(Integer)


class Task(db.Model):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    tag = Column(Text)
    subject_id = Column(Integer)
    create_id = Column(Integer)
    class_id = Column(Integer)
    kind_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)
    title = Column(String(100))
    content = Column(String(255))
    pics = Column(String(2000))
    type = Column(Integer)
    ins_id = Column(Integer)

    def __repr__(self):
        return '<Task (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.tag, self.subject_id, self.create_id, self.class_id, self.kind_id, self.create_time,
                  self.is_del, self.title, self.content, self.pics, self.type, self.ins_id)


class TeacherMode(db.Model):
    __tablename__ = 'teacher_mode'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    tag = Column(String(20))
    privilege = Column(String(255))


class TeacherRole(db.Model):
    __tablename__ = 'teacher_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    is_del = Column(Integer)


class TeacherTask(db.Model):
    __tablename__ = 'teacher_task'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer)
    teacher_id = Column(Integer)
    status = Column(Integer)

    def __repr__(self):
        return '<TeacherTask ( %r, %r, %r, %r)>' % (self.id, self.activity_id, self.teacher_id, self.status)


class Term(db.Model):
    __tablename__ = 'term'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    is_grade = Column(String(255))
    is_current = Column(Integer)
    is_history = Column(Integer)
    side = Column(String(255))
    startmonth = Column(Integer)


class TokenSession(db.Model):
    __tablename__ = 'token_session'

    id = Column(Integer, primary_key=True)
    sessionid = Column(String(255))
    token = Column(String(255))


class ToolIndex(db.Model):
    __tablename__ = 'tool_index'

    id = Column(Integer, primary_key=True)
    gid = Column(Integer)
    value = Column(Numeric(10, 0))
    type = Column(String(20))
    year = Column(Integer)
    month = Column(Integer)


class User(db.Model):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    phone = Column(String(20))
    name = Column(String(20))
    password = Column(String(50))
    role_id = Column(Integer)
    kind_id = Column(Integer)
    create_time = Column(Integer)
    is_froze = Column(Integer)
    is_del = Column(Integer)
    is_init = Column(Integer)
    class_ids = Column(String(255))
    thumb = Column(String(100))
    htoken = Column(String(50))
    vertify_code = Column(Integer)
    token = Column(String(32))
    deviceid = Column(String(100))

    def __repr__(self):
        return '<User ( %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.phone, self.name, self.password, self.role_id, self.kind_id, self.create_time,
                  self.is_froze, self.is_del, self.is_init, self.class_ids, self.thumb, self.htoken, self.vertify_code,
                  self.token, self.deviceid)


class UserCopy(db.Model):
    __tablename__ = 'user_copy'

    id = Column(Integer, primary_key=True)
    phone = Column(String(20))
    name = Column(String(20))
    password = Column(String(50))
    role_id = Column(Integer)
    kind_id = Column(Integer)
    create_time = Column(Integer)
    is_froze = Column(Integer)
    is_del = Column(Integer)
    is_init = Column(Integer)
    class_ids = Column(String(255))
    thumb = Column(String(100))


class UserLog(db.Model):
    __tablename__ = 'user_log'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    controller = Column(String(20), index=True)
    action = Column(String(20), index=True)
    create_time = Column(Integer, index=True)
    getdata = Column(String(255))
    postdata = Column(Text)
    ip = Column(String(20))
    role = Column(Integer)
    kind_id = Column(Integer)


class UserMessage(db.Model):
    __tablename__ = 'user_message'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message_id = Column(Text)


class Weibo(db.Model):
    __tablename__ = 'weibo'

    id = Column(Integer, primary_key=True)
    create_id = Column(String(20), index=True)
    create_type = Column(Integer)
    class_id = Column(Integer, index=True)
    create_time = Column(Integer, index=True)
    is_del = Column(Integer)
    content = Column(Text)
    thumbs = Column(String(5000))
    pics = Column(String(2000))
    audio = Column(String(300))
    video = Column(String(300))
    kind_id = Column(Integer)
    subject_id = Column(Integer)
    task_id = Column(Integer)
    activity_id = Column(Integer)
    is_draft = Column(Integer)
    last_edit_id = Column(String(255))
    last_edit_time = Column(Integer)
    comments = Column(Integer)
    likes = Column(Integer)
    picks = Column(Integer)
    unpicks = Column(Integer)
    is_private = Column(Integer)
    parent_id = Column(Integer)
    stus = Column(String(255))
    stu_ids = Column(String(1000))
    is_task = Column(Integer)
    title = Column(String(255))
    done_task = Column(Integer, index=True)
    ignore_id = Column(String(255))
    term_id = Column(Integer)
    is_old = Column(Integer)
    is_comment = Column(Integer)
    unsee = Column(String(1000))
    tag = Column(String(255))
    task_type = Column(Integer)
    is_notice = Column(Integer)
    notice_time = Column(String(20))
    hour = Column(Integer)
    audio_second = Column(String(255))

    def __repr__(self):
        return '<Weibo (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r)>' \
               % (self.id, self.create_id, self.create_type, self.class_id, self.create_time, self.is_del, self.content,
                  self.thumbs, self.pics, self.audio, self.video, self.kind_id, self.subject_id, self.task_id,
                  self.activity_id, self.is_draft, self.comments, self.likes, self.picks, self.unpicks, self.is_private,
                  self.parent_id, self.stus, self.is_task, self.title, self.done_task, self.ignore_id, self.term_id,
                  self.is_comment, self.unsee, self.tag, self.task_type, self.is_notice, self.audio_second)


class WeiboCopy(db.Model):
    __tablename__ = 'weibo_copy'

    id = Column(Integer, primary_key=True)
    create_id = Column(String(20), index=True)
    create_type = Column(Integer)
    class_id = Column(Integer)
    create_time = Column(Integer)
    is_del = Column(Integer)
    content = Column(Text)
    thumbs = Column(String(5000))
    pics = Column(String(2000))
    audio = Column(String(300))
    video = Column(String(300))
    kind_id = Column(Integer)
    subject_id = Column(Integer)
    task_id = Column(Integer)
    activity_id = Column(Integer)
    is_draft = Column(Integer)
    last_edit_id = Column(String(255))
    last_edit_time = Column(Integer)
    comments = Column(Integer)
    likes = Column(Integer)
    picks = Column(Integer)
    unpicks = Column(Integer)
    is_private = Column(Integer)
    parent_id = Column(Integer)
    stus = Column(String(255))
    stu_ids = Column(String(1000))
    is_task = Column(Integer)
    title = Column(String(255))
    done_task = Column(Integer)
    ignore_id = Column(String(255))
    term_id = Column(Integer)
    is_old = Column(Integer)
    is_comment = Column(Integer)


class WeiboRead(db.Model):
    __tablename__ = 'weibo_read'

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer, index=True)
    uid = Column(Integer, index=True)
    create_time = Column(Integer)

    def __repr__(self):
        return '<WeiboRead (%r, %r, %r, %r)>' % (self.id, self.weibo_id, self.uid, self.create_time)


class Ibook(db.Model):
    __tablename__ = 'ibook'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    term_id = Column(Integer)
    start_time = Column(Integer)
    end_time = Column(Integer)
    sign_guardian = Column(String(100))
    type = Column(Integer, server_default=text("'1'"))
    last_edit_time = Column(Integer)
    is_del = Column(Integer, server_default=text("'0'"))
    cover_img = Column(String(255))
    secret_audio = Column(String(300))
    secret_content = Column(Text)
    future_letter_audio = Column(String(300))
    future_letter_content = Column(Text)
    unpick_sheet = Column(String(255))
    future_letter_create_time = Column(Integer)
    send_future_letter = Column(Integer, server_default=text("'0'"))
    is_private = Column(Integer, server_default=text("'0'"))
    cache_length = Column(Integer, server_default=text("'0'"))
    star = Column(Integer, server_default=text("'0'"))
    download_path = Column(String(200))

    def __repr__(self):
        return '<Ibook (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, )>' % \
               (self.id, self.uid, self.term_id, self.start_time, self.end_time, self.sign_guardian, self.type, self.last_edit_time,
                self.is_del, self.cover_img, self.secret_audio, self.secret_content, self.future_letter_audio, self.future_letter_content,
                self.unpick_sheet, self.future_letter_create_time, self.send_future_letter, self.is_private, self.cache_length,
                self.star, self.download_path)


class IbookAddres(db.Model):
    __tablename__ = 'ibook_address'

    id = Column(Integer, primary_key=True)
    province = Column(String(20))
    city = Column(String(20))
    area = Column(String(20))
    address = Column(String(100))
    phone = Column(String(20))
    uid = Column(Integer)
    name = Column(String(20))


class IbookCoupon(db.Model):
    __tablename__ = 'ibook_coupon'

    id = Column(Integer, primary_key=True)
    code = Column(String(255))
    value = Column(Integer)
    uid = Column(Integer)
    start_time = Column(Integer)
    end_time = Column(Integer)
    create_time = Column(Integer)
    is_use = Column(Integer, server_default=text("'0'"))
    is_give = Column(Integer, server_default=text("'0'"))
    is_del = Column(Integer, server_default=text("'0'"))
    text = Column(String)


class IbookDownloadUser(db.Model):
    __tablename__ = 'ibook_download_user'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    book_type = Column(Integer)
    status = Column(Integer, server_default=text("'1'"))
    is_del = Column(Integer, server_default=text("'0'"))
    create_time = Column(Integer)
    path = Column(String(255))
    send_id = Column(Integer, server_default=text("'0'"))

    def __repr__(self):
        return '<IbookDownloadUser (%r, %r, %r, %r, %r, %r, %r, %r)>' % \
               (self.id, self.book_id, self.book_type, self.status, self.is_del, self.create_time, self.path, self.send_id)


class IbookGrade(db.Model):
    __tablename__ = 'ibook_grade'

    id = Column(Integer, primary_key=True)
    grade_id = Column(Integer)
    term_id = Column(Integer)


class IbookGradeConfig(db.Model):
    __tablename__ = 'ibook_grade_config'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer)
    after = Column(String(255))
    term_id = Column(Integer)
    grade_id = Column(Integer)


class IbookGradePage(db.Model):
    __tablename__ = 'ibook_grade_page'

    id = Column(Integer, primary_key=True)
    grade_id = Column(Integer)
    term_id = Column(Integer)
    title = Column(String(255))
    content = Column(Text)
    background = Column(String(255))
    pic = Column(String(255))
    is_del = Column(Integer, server_default=text("'0'"))
    type = Column(Integer, server_default=text("'1'"))
    sort = Column(Integer, server_default=text("'0'"))
    after = Column(String(50))
    color = Column(String(10))
    background_index = Column(Integer)


class IbookOrder(db.Model):
    __tablename__ = 'ibook_order'

    id = Column(Integer, primary_key=True)
    bid = Column(Integer)
    create_time = Column(Integer)
    uid = Column(Integer)
    status = Column(Integer, server_default=text("'0'"))
    phone = Column(String(20))
    address_id = Column(Integer, server_default=text("'0'"))
    coupon_id = Column(Integer, server_default=text("'0'"))
    price = Column(Numeric(10, 1))
    note = Column(String(255))
    term_id = Column(Integer)
    cover = Column(Integer, server_default=text("'0'"))
    num = Column(Integer, server_default=text("'1'"))
    pages = Column(Integer, server_default=text("'0'"))
    is_del = Column(Integer, server_default=text("'0'"))
    is_draft = Column(Integer, server_default=text("'1'"))
    order_id = Column(String(20))
    pay_type = Column(Integer, server_default=text("'0'"))
    coupon_price = Column(Integer)
    tracking_number = Column(String(20))
    tracking_name = Column(String(20))
    address_name = Column(String(1000))
    tracking_time = Column(Integer)
    tracking_star_time = Column(Integer)

    def __repr__(self):
        return '<IbookOrder (%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, )>' % \
               (self.id, self.bid, self.create_time, self.uid, self.status, self.phone, self.address_id, self.coupon_id,
                self.price, self.note, self.term_id, self.cover, self.num, self.pages, self.is_del, self.is_draft,
                self.order_id, self.pay_type, self.coupon_price, self.tracking_name, self.tracking_number, self.address_name,
                self.tracking_time, self.tracking_star_time)


class IbookPage(db.Model):
    __tablename__ = 'ibook_page'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    type = Column(Integer)
    data = Column(String(100), index=True)
    is_del = Column(Integer, server_default=text("'0'"))
    url = Column(String(1000))

    def __repr__(self):
        return '<IbookPage (%r, %r, %r, %r, %r, %r, )>' % (self.id, self.book_id, self.type, self.data, self.is_del, self.url)


class IbookPhoto(db.Model):
    __tablename__ = 'ibook_photo'

    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer)
    object = Column(String(255))
    rs = Column(Integer, server_default=text("'0'"))
    width = Column(Integer, server_default=text("'0'"))
    height = Column(Integer, server_default=text("'0'"))
    type = Column(Integer)
    is_del = Column(Integer, server_default=text("'0'"))
    weibo_id = Column(Integer)
    x = Column(Integer, server_default=text("'0'"))
    y = Column(Integer, server_default=text("'0'"))
    master_id = Column(Integer)
    crop = Column(String(100), server_default=text("'0'"))


class IbookSecretFuture(db.Model):
    __tablename__ = 'ibook_secret_future'

    id = Column(Integer, primary_key=True)
    secret_audio = Column(String(300))
    secret_content = Column(Text)
    future_letter_audio = Column(String(300))
    future_letter_content = Column(Text)
    future_letter_create_time = Column(Integer)
    send_future_letter = Column(Integer, server_default=text("'0'"))
    is_private = Column(Integer, server_default=text("'0'"))
    uid = Column(Integer)
    term_id = Column(Integer)


class IbookSend(db.Model):
    __tablename__ = 'ibook_send'

    id = Column(Integer, primary_key=True)
    code = Column(String(6))
    download_id = Column(Integer)
    uid = Column(Integer)
    book_id = Column(Integer)
    term_id = Column(Integer)

    def __repr__(self):
        return '<IbookSend (%r, %r, %r, %r, %r, %r, )>' % (self.id, self.code, self.download_id, self.uid, self.book_id, self.term_id)


class IbookStatu(db.Model):
    __tablename__ = 'ibook_status'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, server_default=text("'0'"))
    book_id = Column(Integer)
    sheet = Column(String(255))

    def __repr__(self):
        return '<IbookStatu (%r, %r, %r, %r, )>' % (self.id, self.subject_id, self.book_id, self.sheet)


class IbookUnpickview(db.Model):
    __tablename__ = 'ibook_unpickview'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, server_default=text("'0'"))
    book_id = Column(Integer)
    view = Column(String(255))


class IbookWeibo(db.Model):
    __tablename__ = 'ibook_weibo'

    id = Column(Integer, primary_key=True)
    weibo_id = Column(Integer, index=True)
    is_del = Column(Integer, server_default=text("'0'"))
    author = Column(String(255))
    create_type = Column(Integer, server_default=text("'1'"))
    title = Column(String(255))
    content = Column(Text)
    photos = Column(String(2000))
    audio = Column(String(300))
    subject_name = Column(String(255))
    create_time = Column(Integer)
    book_id = Column(Integer, index=True)
    subject_id = Column(Integer, index=True, server_default=text("'0'"))
    tag = Column(String(255))
    has_audio_pick = Column(Integer, server_default=text("'1'"))
    audio_second = Column(String(255))
