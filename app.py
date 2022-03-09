import os
import secrets
from PIL import Image
from flask import Flask,render_template,request,flash,redirect,url_for
from flask_socketio import SocketIO,emit,join_room,leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from forms import RegistrationForm,LoginForm,CreateRoomForm,EditProfileForm
from flask_login import LoginManager, current_user, login_user,UserMixin,logout_user,login_required
#instaciating Flask app
app = Flask(__name__)
socket = SocketIO(app, cors_allowed_origins="*")
# Setting database session to your database to use flask-sessions
app.config['SESSION_TYPE'] = 'sqlalchemy'

app.secret_key = 'your secret key here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

# Database we are using for flask-sessions
app.config['SESSION_SQLALCHEMY'] = db


# Instanciating flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    pfp = db.Column(db.String(50),nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    def __repr__(self):
        return f'User({self.username},{self.email},{self.pfp})'

class Global_rooms(db.Model):
    room_id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(60), nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    topic = db.Column(db.String(20))
    admin = db.Column(db.Integer, db.ForeignKey('user.id'),nullable=False)

    def __repr__(self):
        return f'Room({self.name},{self.desc},{self.admin})'
class Participants(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String, db.ForeignKey('user.username'),nullable=False)
    room = db.Column(db.Integer, db.ForeignKey('global_rooms.room_id'),nullable=False)

    def __repr__(self):
        return f'Participant({self.id},{self.username},{self.room})'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def add_participant(room,username):
    participant = Participants(username=username,room=room)
    db.session.add(participant)
    db.session.commit()
    return f'{username} added to room {room}'

def remove_participant(username):
    Participants.query.filter_by(username=username).delete()

def get_room(id):
    room = Global_rooms.query.get(id)
    return room

def save_pfp(form_pfp):
    # a random 8 digit filename for saving so that filenames dont get duplicate
    hex_file_name_gen = secrets.token_hex(8)
    name,ext = os.path.splitext(form_pfp.filename)
    final_filename_for_saving = hex_file_name_gen + ext
    pic_saving_path = os.path.join(app.root_path,'static/pfps',final_filename_for_saving)

    image = Image.open(form_pfp)
    image.thumbnail((125,125))
    image.save(pic_saving_path)
    prev_picture = os.path.join(app.root_path, 'static/pfps', current_user.pfp)
    if os.path.exists(prev_picture) and current_user.pfp != 'default.jpg':
        os.remove(prev_picture)
    return final_filename_for_saving

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        if User.query.filter_by(username=form.username.data).first():
            validation_error_message = 'Username already taken. Please choose different one.'
            return render_template('register.html', username_error=validation_error_message,form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            validation_error_message = 'Email Already Registered. Please Log in.'
            return render_template('register.html', email_error=validation_error_message,form=form)
        else:
            user_hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data,email=form.email.data,password=user_hashed_password)
            db.session.add(user)
            db.session.commit()
            # Email otp confirmation to activate account
            flash(f'Account created successfully, {form.username.data}. Lets go!','success')
            login_user(user,remember=True)
            return redirect(url_for('home'))
    return render_template('register.html', form=form)

@app.route('/')
def home():
    # If previously joined any room then removing the user from participation in that room
    users = User.query.all()
    rooms = Global_rooms.query.all()
    return render_template('home.html',rooms=rooms,user=User)

@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm(request.form)
    if request.method=='POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember=form.remember.data)
            flash(f'Logged in Successfully as {user.username}!','success')
            return redirect(url_for('home'))
        if user==None:
            flash('Email not registered with us. Join us now!','info')
            return redirect(url_for('register'))
        else:
            flash('Incorrect Password. Click on Forgot Password to change.','danger')
            return redirect(url_for('login'))

        
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out','info')
    return redirect(url_for('home'))

@app.route('/profile',methods=['GET','POST'])
@login_required
def user_account():
    form = EditProfileForm()
    
    if request.method=='POST' and form.validate_on_submit():
        if form.pfp.data:
            pfp_name = save_pfp(form.pfp.data)
            current_user.pfp = pfp_name
            db.session.commit()
            flash('Account has been successfully updated','success')
        if form.username.data != current_user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken. Please choose different one.','danger')
            else:
                current_user.username = form.username.data
                db.session.commit()
                flash('Your account has been updated successfully!','success')
        
        user_pfp = url_for('static',filename='pfps/'+current_user.pfp)
        return render_template('account.html',pic = user_pfp,form=form)
    if request.method=='GET':
        form.username.data = current_user.username
    user_pfp = url_for('static',filename='pfps/'+current_user.pfp)
    return render_template('account.html',pic = user_pfp,form=form)

@app.route('/create_room',methods=['GET','POST'])
@login_required
def create_room():
    form = CreateRoomForm(request.form)
    if request.method=='POST' and form.validate():
        if Global_rooms.query.filter_by(admin=current_user.id).first():
            flash('Only 1 room is allowed to be made by each user. Please delete existing room to make another one.','info')
            return render_template('create_room.html',form=form)
        else:
            room = Global_rooms(name = form.room_name.data,desc=form.desc.data,topic = form.topic.data,admin=current_user.id)
            db.session.add(room)
            db.session.commit()
            flash(f'Room {form.room_name.data} Successfully created!','success')
            return redirect(url_for('home'))
    return render_template('create_room.html',form=form)

@app.route('/friends')
def friends():
    return render_template('friends.html')

@app.route('/rooms/private')
def private():
    return render_template('private_rooms.html')

@app.route('/room/<room_id>',methods=['GET','POST'])
@login_required
def sessions(room_id):
    if Global_rooms.query.filter_by(room_id=room_id).first():
        user_pfp = url_for('static',filename='pfps/'+current_user.pfp)
        room = get_room(room_id)
        return render_template('chatroom.html',pfp=user_pfp,username = current_user.username,room = room)
    else:
        return 'room not found',404
@socket.on('join')
def joined(data):
    join_room(data['room'])
    emit('joined_user_message',data,room=data['room'])

@socket.on('send_message')
def handle_my_custom_event(data):
    emit('recieved_message', data,room=data['room'])

@socket.on('leave_room')
def handle_leave_room_event(data):
    leave_room(data['room'])
    emit('leave_room_message', data, room=data['room'])
    
if __name__ == '__main__':
    socket.run(app)
