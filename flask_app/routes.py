from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import current_app as app
from flask import Response
from flask import render_template, redirect, request, session, url_for, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from .utils.database.database import database
from werkzeug.datastructures import ImmutableMultiDict
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

@app.route('/logout')
def logout():
	session.pop('email', default=None)
	return redirect('/')

   
#######################################################################################
# PAGES
#######################################################################################
@app.route('/')
def root():
	return redirect('/home')

@app.route('/home')
def home():
    return render_template('home.html',user=getUser())


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data:
            response = json.dumps({'success': 0, 'error': 'Invalid or missing JSON'})
            return Response(response, status=400, mimetype='application/json')

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            response = json.dumps({'success': 0, 'error': 'Email and password required'})
            return Response(response, status=400, mimetype='application/json')

        result = db.createUser(email=email, password=password, role='guest')

        if result['success']:
            response = json.dumps({'success': 1, 'message': 'User registered successfully.'})
            return Response(response, status=200, mimetype='application/json')
        else:
            response = json.dumps({'success': 0, 'error': result['error']})
            return Response(response, status=200, mimetype='application/json')

    return render_template('register.html',user=getUser())



@app.route('/schedule')
@login_required
def schedule():
    return render_template('schedule.html',user=getUser())

@app.route('/event_join')
@login_required
def join_event():
    user_email = getUser()

    # Get events where the user is an invitee
    invited_events = db.get_invited_events(user_email)

    # Render a list of events
    return render_template('event_join.html', events=invited_events, user_email=user_email)



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
    return render_template('event_create.html',user=getUser())

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
    user_email = getUser()
    event = db.get_event_by_id(event_id)
    
    if not event:
        return "Event not found", 404
    
    # Ensure access is restricted to the creator or an invited user
    if user_email != event['creator_email'] and user_email not in event['invitees']:
        return "Access Denied", 403

    return render_template('event_page.html', event=event,user=getUser())

@app.route('/update_availability', methods=['POST'])
@login_required
def update_availability():
    # Get the JSON data from the request body
    data = request.get_json()

    event_id = int(data.get('event_id'))
    availability_list = data.get('availability', [])
    user_email = getUser()
    
    # Save all availability data at once
    result = db.save_availability(event_id, user_email, availability_list)
    
    if result.get('success'):
        # Emit Socket.IO event to notify all clients about the update
        socketio.emit('availability_updated', {
            'event_id': event_id,
            'timestamp': datetime.now().isoformat()
        }, room=f'event_{event_id}')
        
        return json.dumps({'success': True, 'message': result.get('message')})
    else:
        return json.dumps({'success': False, 'error': result.get('error')}), 400

@app.route('/get_availability')
@login_required
def get_availability():
    try:
        event_id = int(request.args.get('event_id'))
        user_email = getUser()

        availability = db.get_availability(event_id, user_email)

        # Convert date/time/timedelta to strings
        for entry in availability:
            if 'date' in entry and hasattr(entry['date'], 'strftime'):
                entry['date'] = entry['date'].strftime('%Y-%m-%d')
            if 'time' in entry:
                time_val = entry['time']
                if hasattr(time_val, 'strftime'):
                    entry['time'] = time_val.strftime('%H:%M:%S')
                else:
                    # Handle timedelta -> convert to HH:MM:SS string
                    total_seconds = int(time_val.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    entry['time'] = f"{hours:02}:{minutes:02}:{seconds:02}"

        return Response(json.dumps(availability), mimetype='application/json')

    except Exception as e:
        print("Error in /get_availability:", e)
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')

@app.route('/get_group_availability')
@login_required
def get_group_availability():
    event_id = request.args.get('event_id')
    results = db.get_group_availability(event_id)
    return Response(json.dumps(decimal_to_float(results)), mimetype='application/json')

def decimal_to_float(obj):
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()  # or str(obj) if preferred
    else:
        return obj

#######################################################################################
# SOCKET.IO EVENT HANDLERS
#######################################################################################

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_event')
def on_join_event(data):
    """Join a room for a specific event to receive updates about it"""
    event_id = data.get('event_id')
    
    if event_id:
        # Create a room name based on the event ID
        room = f'event_{event_id}'
        join_room(room)
        print(f'Client joined room: {room}')
        emit('joined_event', {'status': 'success', 'event_id': event_id}, room=room)

@socketio.on('leave_event')
def on_leave_event(data):
    """Leave the room for a specific event"""
    event_id = data.get('event_id')
    
    if event_id:
        room = f'event_{event_id}'
        leave_room(room)
        print(f'Client left room: {room}')

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