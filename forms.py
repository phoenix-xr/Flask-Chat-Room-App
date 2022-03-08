from flask_wtf import FlaskForm
from flask_wtf.file import FileField,FileAllowed
from wtforms import StringField,EmailField,PasswordField,SubmitField,BooleanField
from wtforms.validators import DataRequired, Length,Email

class RegistrationForm(FlaskForm):
    username = StringField('Make your username',validators = [DataRequired(),Length(2,30)])
    email = EmailField('Email',validators = [DataRequired(),Email()])
    password = PasswordField('Password',validators = [DataRequired(),Length(8,20)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = EmailField('Enter your Email',validators = [DataRequired(),Email()])
    password = PasswordField('Password',validators = [DataRequired()])
    submit = SubmitField('Login')
    remember= BooleanField('Remember me')

class CreateRoomForm(FlaskForm):
    room_name = StringField('Room Name',validators=[DataRequired(),Length(2,60)])
    desc = StringField('Room Description (Optional)')
    topic = StringField('Room Topic')
    submit = SubmitField('Create')

class EditProfileForm(FlaskForm):
    username =  StringField('Make your username',validators = [Length(2,30)])
    pfp = FileField('Choose Profile Picture',validators=[FileAllowed(['jpg','png'])])
    submit = SubmitField('Confirm')