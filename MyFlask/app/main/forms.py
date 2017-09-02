#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __author__ = 'yaphetsglhf'

from wtforms import StringField, TextAreaField, SubmitField, BooleanField, SelectField, ValidationError
from flask_wtf import FlaskForm
from wtforms.validators import Length, DataRequired, Email, Regexp
from ..models import FlaskRole, FlaskUser
from flask_pagedown.fields import PageDownField


class EditProfileForm(FlaskForm):
    fullname = StringField('Full name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(1, 64),
                                                   Regexp('^[A-Za-z][A-Za-z0-9._]*$', 0, 'Usernames must have only letters,numbers, dots or underscores.')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    fullname = StringField('Fullname', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in FlaskRole.query.order_by(FlaskRole.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and FlaskUser.query.filter_by(email=field.data).first():
            raise ValidationError("Email already exists!")

    def validate_username(self, field):
        if field.data != self.user.username and FlaskUser.query.filter_by(username=field.data).first():
            raise ValidationError("Username already exists!")


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Submit')
