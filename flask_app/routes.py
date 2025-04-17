from flask import current_app as app
from flask import Response
from flask import render_template, redirect, request, session, url_for, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from .utils.database.database  import database
from werkzeug.datastructures   import ImmutableMultiDict
from pprint import pprint
import json
import random
import functools
from . import socketio
db = database()


#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "email" not in session:
            return redirect(url_for("home", next=request.url))
        return func(*args, **kwargs)
    return secure_function

def getUser():
    if 'email' in session:
        return db.reversibleEncrypt('decrypt', session['email'])
    return 'Unknown'


@app.route('/processlogin', methods = ["POST","GET"])
def processlogin():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    result = db.authenticate(email, password)

    # Track failed login attempts in session
    if 'failed_attempts' not in session:
        session['failed_attempts'] = 0

    # Use authenticate method from db
    if result.get('success') == 1:
        user = result.get('user', {})
        session['email'] = db.reversibleEncrypt('encrypt', email)
        return json.dumps({'success': True})
    else:
        session['failed_attempts'] += 1
        return json.dumps({'success': 0, 'fail_count': session['failed_attempts']})


   
#######################################################################################
# PAGES
#######################################################################################
@app.route('/')
def root():
	return redirect('/home')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/schedule')
@login_required
def schedule():
    return render_template('schedule.html')

@app.route('/event_create', methods=['GET', 'POST'])
@login_required
def event_create():
    if request.method == 'POST':
        # Collect form data from the POST request
        event_name = request.form.get('event_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        daily_start_time = request.form.get('daily_start_time')
        daily_end_time = request.form.get('daily_end_time')
        invitee_emails = request.form.get('invitee_emails')
        creator_email = getUser()
        event_id = db.create_event(event_name, creator_email, start_date, end_date, daily_start_time, daily_end_time, invitee_emails)

        # Redirect the user to the event page or another appropriate page
        return redirect(url_for('event_page', event_id=event_id))  # Redirect to the event page after creation

    # For GET requests, render the event creation form
    return render_template('event_create.html')

@app.route('/process_event_create', methods=["POST"])
@login_required
def process_event_create():
    event_name = request.form.get('event_name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    invitees = request.form.get('invitees')

    creator_email = getUser()
    invitee_list = [email.strip() for email in invitees.split(',') if email.strip()]

    # Store event in database
    result = db.create_event(
        name=event_name,
        creator_email=creator_email,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        invitees=invitee_list
    )

    if result.get('success'):
        event_id = result.get('event_id')
        return redirect(url_for('event_page', event_id=event_id))  
    else:
        return "Failed to create event: " + result.get('error', 'Unknown error'), 400



@app.route('/event_page/<event_id>')
@login_required
def event_page(event_id):
    
    event = db.get_event_by_id(event_id)

    print(event)
    if not event:
        return "Event not found", 404

    return render_template('event_page.html', event=event)

@app.route('/update_availability', methods=['POST'])
@login_required
def update_availability():
    event_id = request.form['event_id']
    date = request.form['date']
    time = request.form['time']
    mode = request.form['mode']
    user_email = getUser()

    # Save the availability to the database
    db.save_availability(event_id, user_email, date, time, mode)
    return '', 204

@app.route('/get_availability')
@login_required
def get_availability():
    event_id = request.args.get('event_id')
    user_email = getUser()

    # Retrieve availability data from the database
    availability = db.get_availability(event_id, user_email)

    # Manually convert to JSON and return as a Response
    return Response(json.dumps(availability), mimetype='application/json')

#######################################################################################
# OTHER
#######################################################################################
@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


