# -*- coding: utf-8 -*-

"""
The forms used on the site.
"""

from flaskext.wtf import (
	Form, 
	TextField, TextAreaField, SelectField, IntegerField, 
	PasswordField, DateField, DateTimeField, BooleanField,
	QuerySelectField, RadioField, HiddenField,
	Required, Email, URL, Optional, ValidationError)

# wtforms.ext.sqlalchemy.fields.

import re, logging
from data import COUNTRIES
from models import RegistrationProfile, Event, Location, Audit

def validate_unique_email(form, field):
	existing = RegistrationProfile.query.filter(
		RegistrationProfile.email==field.data).first()
	if existing:
		raise ValidationError('E-Mail already is use.')

def validate_unique_event_name(form, field):
	pass
	# existing = Event.query.filter(
	# 	Event.name==field.data).first()
	# if existing:
	# 	raise ValidationError('An event with such a name already exists.')

def validate_capacity(form, field):
	try:
		if int(field.data) < 0:
			raise ValidationError('Only positive numbers.')
	except ValueError:
		raise ValidationError('An integer is required.')

def validate_enrollment_subjects(form, field):
	subjects = []
	for key, value in form.data.items():
		if key.startswith('subject_'):
			if value == True:
				subjects.append(key.split('_')[1])
	if not 'de' in subjects:
		raise ValidationError(u'Eine Prüfung in Deutsch ist Pflicht.')
	if len(subjects) > 3:
		raise ValidationError(u'Sie können sich in maximal drei Sprachen (inkl. Deutsch) prüfen lassen.')
	if len(subjects) < 2:
		raise ValidationError(u'Sie müssen in mindestens einer Fremdsprache den Eignungsprüfungstest ablegen.')

# def validate_login_credentials(form):

class EnrollmentForm(Form):
	audit = QuerySelectField('Audit')
	# subjects = TextField("Subjects")
	subject_de = BooleanField(u"Deutsch")
	subject_en = BooleanField(u"Englisch")
	subject_ru = BooleanField(u"Russisch")
	subject_fr = BooleanField(u"Französisch")
	subject_es = BooleanField(u"Spanisch")
	subject_hidden = HiddenField(u"Sprachauswahl", validators=[validate_enrollment_subjects])
	
	# def validate(self):
	# 	validate_enrollment_subjects(self, None)
	# 	super(EnrollmentForm, self).validate()

class LoginForm(Form):
	username = TextField("E-Mail", validators=[Email(), Required()])
	password = PasswordField("Password", validators=[Required()])

class EventForm(Form):
	name = TextField("Name", validators=[Required(), validate_unique_event_name])
	description = TextField("Description")
	registration_opens = DateTimeField('Registration opens', validators=[Required()], format='%d.%m.%Y %H:%M:%S')
	registration_closes = DateTimeField('Registration closes', validators=[Required()], format='%d.%m.%Y %H:%M:%S')

class LocationForm(Form):
	name = TextField("Name", validators=[Required(), validate_unique_event_name])
	capacity = TextField("Capacity", validators=[validate_capacity])

	zipcode = TextField("Zipcode", validators=[Required()])
	city = TextField("City", validators=[Required()])
	street = TextField("Street", validators=[Required()])
	country = SelectField("Country", choices=COUNTRIES, validators=[Required()])

	address_additions = TextField("Additions")
	google_maps_url = TextField("Google Maps URL")
	

class AuditForm(Form):
	active = BooleanField()
	# event = QuerySelectField('Event', query_factory=lambda: Event.query.all())
	location = QuerySelectField('Location', query_factory=lambda: Location.query.all())
	starts = DateTimeField('Starts', validators=[Required()], format='%d.%m.%Y %H:%M:%S')
	ends = DateTimeField('Ends', validators=[Required()], format='%d.%m.%Y %H:%M:%S')
	
class RegistrationForm(Form):
	"""
	For for manually adding a Job.
	"""
	first_name = TextField("First Name", validators=[Required()])
	last_name = TextField("Last Name", validators=[Required()])
	email = TextField("E-Mail", validators=[Email(), Required(), validate_unique_email])
	
	password = PasswordField("Password", validators=[Required()])
	confirm = PasswordField("Confirm Password", validators=[Required()])

	
	dob = DateField('Date of Birth', validators=[Required()], format='%d.%m.%Y')
	identifier_id = TextField("Identifier ID", validators=[Required()])

	zipcode = TextField("Zipcode", validators=[Required()])
	city = TextField("City", validators=[Required()])
	street = TextField("Street", validators=[Required()])
	country = SelectField("Country", choices=COUNTRIES, validators=[Required()])

