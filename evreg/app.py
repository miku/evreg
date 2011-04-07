# -*- coding: utf-8 -*-

from flask import (Flask, redirect, url_for, render_template, request, flash, g, session)
from forms import RegistrationForm, LoginForm, EventForm, AuditForm, LocationForm, EnrollmentForm
from database import db_session
import json
from functools import wraps
from models import RegistrationProfile, User, Event, Location, Audit, Enrollment
from werkzeug import generate_password_hash


import datetime

app = Flask(__name__)
app.config.from_pyfile('app.dev.cfg')

from flaskext.mail import Mail, Message
mail = Mail(app)

@app.template_filter()
def humanize_languages(value):
	subjects = json.loads(value)
	mapping = {
		'de' : u'Deutsch',
		'en' : u'Englisch',
		'fr' : u'Französisch',
		'ru' : u'Russisch',
		'es' : u'Spanisch'
	}
	try:
		return ', '.join( [ mapping[s] for s in subjects ] )
	except KeyError:
		pass
	return value

def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if g.user is None:
			return redirect(url_for('login', next=request.url))
		return f(*args, **kwargs)
	return decorated_function	

def logged_in_user_or_404():
	if 'user_id' in session and session['user_id']:
		return User.query.get(session['user_id'])
	return render_template('page_not_found.html'), 404

# @app.after_request
# def shutdown_session(response):
#	db_session.remove()
#	return response

# def connect_db():
#	  """Returns a new connection to the database."""
#	  return sqlite3.connect(app.config['DATABASE_URI'])
	
@app.before_request
def before_request():
	"""Make sure we are connected to the database each request and look
	up the current user so that we know he's there.
	"""
	g.user = None
	if 'user_id' in session and session['user_id']:
		g.user = User.query.get(session['user_id'])

@app.after_request
def after_request(response):
	"""Closes the database again at the end of the request."""
	db_session.remove()
	return response

@app.route('/')
def root():
	return redirect(url_for('index'))

@app.route('/index') 
def index():
	return render_template('index.html')

@app.route('/profile')
def profile():
	user = logged_in_user_or_404()
	now = datetime.datetime.now()
	events = Event.query.filter(
		Event.registration_opens < now).filter(
		Event.registration_closes > now)
	enrollments = Enrollment.query.filter(Enrollment.user==user)
	return render_template('profile.html', **locals())

@app.route('/event/<int:event_id>/enroll', methods=['GET', 'POST'])
@login_required
def enroll(event_id):
	user = logged_in_user_or_404()
	event = Event.query.get(event_id)
	form = EnrollmentForm()
	form.audit.query = Audit.query.filter(Audit.event==event)
	if form.validate_on_submit():
		enrollment = Enrollment()
		enrollment.user = user
		enrollment.user_id = user.id
		enrollment.audit = form.audit.data
		enrollment.audit_id = enrollment.audit.id
		enrollment.enrollment_date = datetime.datetime.now()
		
		subjects = []
		if form.subject_de.data:
			subjects.append('de')
		if form.subject_en.data:
			subjects.append('en')
		if form.subject_ru.data:
			subjects.append('ru')
		if form.subject_fr.data:
			subjects.append('fr')
		if form.subject_es.data:
			subjects.append('es')

		enrollment.subjects = json.dumps(subjects)
		
		if enrollment.audit.available_seats() <= 1:
			flash(u"Sie können sich für diese Prüfung nicht mehr anmelden, da das Maximum der Teilnehmeranzahl erreicht ist. Bitte wählen Sie einen anderen Termin.")
			enrollment = None
		else:
			db_session.add(enrollment)
			db_session.commit()
		return redirect(url_for('profile'))
	return render_template("enroll.html", **locals())

@app.route('/enrollment/<int:enrollment_id>/cancel', methods=['POST'])
def delete_enrollment(enrollment_id):
	enrollment = Enrollment.query.get(enrollment_id)
	db_session.delete(enrollment)
	db_session.commit()
	return redirect(url_for('profile'))

@app.route('/login', methods=['GET', 'POST']) 
def login():
	form = LoginForm()
	if form.validate_on_submit():
		username = unicode(form.username.data)
		password = unicode(form.password.data)
		user = User.query.filter(User.email == username).first()		
		if user and user.check_password(password):
			session['user_id'] = user.id
			if user.is_in('admin'):
				return redirect(url_for('dashboard'))
			else:
				return redirect(url_for('profile'))
		else:
			flash("Could not log in.")
	else:
		form = LoginForm()
	return render_template("auth/login.html", form=form)

@app.route('/logout', ) 
def logout():
	session.pop('user_id', None)
	flash("Successfully logged out.")
	return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
	events = Event.query.all()
	locations = Location.query.all()
	return render_template("admin/dashboard.html", **locals())

@app.route('/register', methods=['GET', 'POST']) 
def register():
	form = RegistrationForm()
	if form.validate_on_submit():
		profile = RegistrationProfile()
		profile.first_name = unicode(form.first_name.data)
		profile.last_name = unicode(form.last_name.data)
		profile.email = unicode(form.email.data)
		profile.password = unicode(generate_password_hash(form.password.data))
		profile.ip_address = unicode(request.remote_addr)
		profile.dob = form.dob.data
		profile.identifier_id= unicode(form.identifier_id.data)
		profile.country = unicode(form.country.data)
		profile.zipcode = unicode(form.zipcode.data)
		profile.city = unicode(form.city.data)
		profile.street = unicode(form.street.data)
		
		profile.username = profile.email
		
		db_session.add(profile)
		db_session.commit()
		# TODO, send email!
		
		with mail.record_messages() as outbox:					
			msg = Message("IALT Registration",
				sender=("IALT Registration", "ialt@uni-leipzig.de"),
				recipients=[profile.email])
			msg.body = "Please activate your Profile under {0}".format(profile.activation_key)
			mail.send(msg)
			
			assert len(outbox) == 1
			assert outbox[0].subject == "IALT Registration"
			assert profile.email in outbox[0].recipients
		
		flash("Registration completed. We've sent you an E-Mail with your activation key.")
		print profile.activation_key
		return redirect(url_for('index'))
	return render_template("auth/register.html", form=form)

@app.route('/activate/<key>')
def activate(key):
	""" Activate profile. Create a new user object. 
		We use the email as username.
	"""
	profile = RegistrationProfile.query.filter(
		RegistrationProfile.activation_key==key).first()
	
	if not profile:
		return render_template("auth/activation_failed.html")

	if not profile.activation_date == None:
		return render_template("auth/already_activated.html")
	
	if profile.expiration_date > datetime.datetime.now():
		user = User()
		user.first_name = profile.first_name
		user.last_name = profile.last_name
		user.email = profile.email
		user.username = profile.email
		user.password = profile.password
		profile.activation_date = datetime.datetime.now()
		user.dob = profile.dob
		user.identifier_id= profile.identifier_id
		user.country = profile.country
		user.zipcode = profile.zipcode
		user.city = profile.city
		user.street = profile.street
		db_session.add(user)
		db_session.add(profile)
		db_session.commit()
		flash("Your account has been activated. You may login now.")
		return redirect(url_for('index'))
	return render_template("auth/activation_expired.html")

# @app.route('/events/')
# def list_events():
#	events = Event.query.all()
#	return render_template('list_events.html', events=events)

@app.route('/event/', methods=['GET', 'POST'])
def create_event():
	form = EventForm()
	if form.validate_on_submit():
		event = Event()
		event.name = unicode(form.name.data)
		event.description = unicode(form.description.data)
		event.registration_opens = form.registration_opens.data
		event.registration_closes = form.registration_closes.data
		db_session.add(event)
		db_session.commit()
		return redirect(url_for('dashboard'))
	return render_template("admin/create_event.html", form=form)

@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
def edit_event(event_id):
	event = Event.query.get(event_id)
	form = EventForm(obj=event)
	if form.validate_on_submit():
		event.name = unicode(form.name.data)
		event.description = unicode(form.description.data)
		event.registration_opens = form.registration_opens.data
		event.registration_closes = form.registration_closes.data
		db_session.add(event)
		db_session.commit()
		return redirect(url_for('show_event', event_id=event.id))
	return render_template("admin/edit_event.html", **locals()) 

@app.route('/event/<int:event_id>', methods=['GET', 'POST'])
def show_event(event_id):
	event = Event.query.get(event_id)
	audits = Audit.query.filter(Audit.event==event)
	return render_template("admin/show_event.html", **locals())
	
@app.route('/event/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
	event = Event.query.get(event_id)
	db_session.delete(event)
	db_session.commit()
	return redirect(url_for('dashboard'))


@app.route('/event/<int:event_id>/audit', methods=['GET', 'POST'])
def create_audit(event_id):
	event = Event.query.get(event_id)
	form = AuditForm()
	if form.validate_on_submit():
		audit = Audit()
		audit.active = form.active.data
		audit.event = event
		audit.location = form.location.data
		audit.starts = form.starts.data
		audit.ends = form.ends.data
		db_session.add(audit)
		db_session.commit()
		return redirect(url_for('show_event', event_id=event.id))
	return render_template("admin/create_audit.html", **locals())

@app.route('/event/<int:event_id>/audit/<int:audit_id>', methods=['GET', 'POST'])
def edit_audit(event_id, audit_id):
	event = Event.query.get(event_id)
	audit = Audit.query.get(audit_id)
	form = AuditForm(obj=audit)
	if form.validate_on_submit():
		audit.active = form.active.data
		audit.event = event
		audit.location = form.location.data
		audit.starts = form.starts.data
		audit.ends = form.ends.data
		db_session.add(audit)
		db_session.commit()
		return redirect(url_for('show_event', event_id=event_id))
	return render_template("admin/edit_audit.html", **locals())

@app.route('/event/<int:event_id>/audit/<int:audit_id>/delete', methods=['POST'])
def delete_audit(event_id, audit_id):
	audit = Audit.query.get(audit_id)
	db_session.delete(audit)
	db_session.commit()
	return redirect(url_for('show_event', eid=event_id))

@app.route('/locations')
def list_locations():
	locations = Location.query.all()
	return render_template('list_locations.html', locations=locations)

@app.route('/location', methods=['GET', 'POST'])
def create_location():
	form = LocationForm()
	if form.validate_on_submit():
		location = Location()
		location.name = form.name.data
		location.capacity = form.capacity.data
		location.country = form.country.data
		location.zipcode = form.zipcode.data
		location.city = form.city.data
		location.street = form.street.data
		
		location.address_additions = form.address_additions.data
		location.google_maps_url = form.google_maps_url.data
		
		db_session.add(location)
		db_session.commit()
		return redirect(url_for('list_locations'))
	return render_template("admin/create_location.html", form=form)

@app.route('/location/<int:lid>')
def show_location(lid):
	location = Location.query.get(lid)
	return render_template("admin/show_location.html", location=location)


if __name__ == "__main__":
	app.run()
