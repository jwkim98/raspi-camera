from flask import Flask, render_template, url_for, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin,
    login_user,
    LoginManager,
    login_required,
    logout_user,
    current_user,
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from camera import VideoCamera
from mail import send_image_mail
from gpiozero import Servo
import os, argparse, serial, time, readchar, signal
import RPi.GPIO as GPIO
import pigpio


app = Flask(__name__)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = os.urandom(24)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

pi_camera = VideoCamera(flip=True)
servo = pigpio.pi()
servo_pin = 21
sensor = 20
position = 1500
alert = False


mail_address = ""


def gen(camera):
    # get camera frame
    while pi_camera.is_activated():
        frame = camera.get_frame()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")
    return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class LoginForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Username"},
    )

    password = PasswordField(
        validators=[InputRequired(), Length(min=8, max=20)],
        render_kw={"placeholder": "Password"},
    )

    submit = SubmitField("Login")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("dashboard"))
    return render_template("login.html", form=form)


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(
        gen(pi_camera), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/left")
@login_required
def left():
    global position
    print("Left")
    if position <= 2000:
        position += 50
    servo.set_servo_pulsewidth(servo_pin, position)
    return "nothing"


@app.route("/right")
@login_required
def right():
    global position
    print("Right")
    if position >= 1000:
        position -= 50
    servo.set_servo_pulsewidth(servo_pin, position)
    return "nothing"


# Take a photo when pressing camera button
@app.route("/picture")
@login_required
def take_picture():
    print("alert on")
    global alert
    alert = True
    return "None"


def handler(signum, frame):
    msg = "stopping server : (y.n)"
    print(msg, end="", flush=True)
    res = readchar.readchar()
    if res == "y":
        pi_camera.stop()
        running = False
        GPIO.cleanup()
        exit(1)
    else:
        print("", end="\r", flush=True)


def alert_detected(channel):
    print("Detected somebody!")
    if alert:
        file_name = pi_camera.take_picture()
        send_image_mail(file_name, mail_address)


if __name__ == "__main__":
    db.session.query(User).delete()
    db.session.commit()

    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--mail", type=str)
    args = parser.parse_args()

    hashed_password = bcrypt.generate_password_hash(args.password)
    new_user = User(username=args.username, password=hashed_password)
    mail_address = args.mail
    del args
    db.session.add(new_user)
    db.session.commit()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(sensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(sensor, GPIO.FALLING, callback=alert_detected, bouncetime=100)

    servo.set_servo_pulsewidth(servo_pin, position)
    signal.signal(signal.SIGINT, handler)

    # serve(app, host="0.0.0.0", port=56742)
    app.run(host="0.0.0.0", debug=False)
