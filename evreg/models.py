# -*- coding: utf-8 -*-

from sqlalchemy import (Column, Integer, Unicode, 
	DateTime, Date, ForeignKey, Boolean, UnicodeText, Table)

from sqlalchemy.orm import (relationship, backref)
from werkzeug import check_password_hash

from database import Base
import datetime
import uuid


class CommonUserMixin(object):
	""" Common User information. 
	"""
	username = Column(Unicode(128), unique=True, nullable=False)
	first_name = Column(Unicode(64), nullable=False)
	last_name = Column(Unicode(64), nullable=False)
	email = Column(Unicode(128), unique=True, nullable=False)
	password = Column(Unicode(128), nullable=False)
	
	dob = Column(Date(), nullable=False)
	identifier_id = Column(Unicode(32), nullable=False)

class AddressMixin(object):
	"""
	Address data upto street level. 
	"""
	zipcode = Column(Unicode(16), nullable=False)
	city = Column(Unicode(128), nullable=False)
	street = Column(Unicode(128), nullable=False)
	country = Column(Unicode(128), nullable=False)

class LastModifiedMixin(object):
	""" Last modified mixin. """
	last_modified = Column(DateTime(), onupdate=datetime.datetime.now)

user_groups = Table('user_groups', Base.metadata,
	Column('user_id', Integer, ForeignKey('users.id')),	
	Column('group_id', Integer, ForeignKey('groups.id'))
)

class Group(Base):
	""" Group for permission management. """
	__tablename__ = 'groups'
	
	id = Column(Integer, primary_key=True)
	name = Column(Unicode(128), unique=True, nullable=False)
	

class User(Base, CommonUserMixin, AddressMixin, LastModifiedMixin):
	""" A site user.
	"""
	__tablename__ = 'users'
	
	id = Column(Integer, primary_key=True)
	
	groups = relationship('Group', secondary=user_groups, backref='users')
	
	def __init__(self, first_name=None, last_name=None, 
		username=None, email=None, password=None, 
		dob=None, identifier_id=None, country=None, zipcode=None, city=None,
		street=None):
		
		self.first_name = first_name
		self.last_name = last_name
		self.username = username
		self.email = email
		self.password = password
		
		self.dob = dob
		self.identifier_id = identifier_id
		
		self.country = country
		self.zipcode = zipcode
		self.city = city
		self.street = street
	
	def check_password(self, password):
		return check_password_hash(self.password, password)
	
	def is_in(self, name):
		""" Group check. """
		for group in self.groups:
			if group.name == name:
				return True
		return False
		

	def __repr__(self):
		return '<User {0}>'.format(self.username)

class RegistrationProfile(Base, CommonUserMixin, AddressMixin):
	""" Registrations have a key, which expires after three days.
	"""
	__tablename__ = 'registration_profiles'

	id = Column(Integer, primary_key=True)
	
	ip_address = Column(Unicode(128), nullable=True)
	activation_key = Column(Unicode(128), unique=True, 
		default=unicode(uuid.uuid4()), nullable=False)
	registration_date = Column(DateTime(), default=datetime.datetime.now())
	activation_date = Column(DateTime(), default=None)
	expiration_date = Column(DateTime(), 
		default=datetime.datetime.now() + datetime.timedelta(3))
	
	def __init__(self, first_name=None, last_name=None, email=None,
		password=None, ip_address=None,
		dob=None, identifier_id=None, country=None, zipcode=None, city=None,
		street=None):
		
		self.first_name = first_name
		self.last_name = last_name
		self.email = email
		self.password = password
		self.ip_address = ip_address

		self.dob = dob
		self.identifier_id = identifier_id
		self.country = country
		self.zipcode = zipcode
		self.city = city
		self.street = street
	
	def __repr__(self):
		return u'<RegistrationProfile {0}>'.format(self.email)


class Event(Base, LastModifiedMixin):
	""" Generic event, mainly described by a name, a description
	and a registration period. """

	__tablename__ = 'events'
	
	id = Column(Integer, primary_key=True)

	name = Column(Unicode(128), nullable=False)
	description = Column(UnicodeText, nullable=True)
	
	registration_opens = Column(DateTime())
	registration_closes = Column(DateTime())
	
	def __init__(self, name=None, description=None, 
		registration_opens=None, registration_closes=None):
		self.name = name
		self.description = description
		self.registration_opens = registration_opens
		self.registration_closes = registration_closes
	
	def __repr__(self):
		return u'<Event {0}>'.format(self.name)

class Location(Base, AddressMixin, LastModifiedMixin):
	""" A location for audits. """

	__tablename__ = 'locations'
		
	id = Column(Integer, primary_key=True)
	
	name = Column(Unicode(256), nullable=False)
	capacity = Column(Integer, nullable=False)

	address_additions = Column(Unicode(256), nullable=True)	
	google_maps_url = Column(Unicode(1024), nullable=True)
	
	def __init__(self, name=None, capacity=None, 
		country=None, zipcode=None, city=None, street=None,
		address_additions=None, google_maps_url=None):
		self.name = name
		self.capacity = capacity
		self.country = country
		self.zipcode = zipcode
		self.city = city
		self.street = street
		self.address_additions = address_additions
		self.google_maps_url = google_maps_url

	def __repr__(self):
		return u'<Location {0}>'.format(self.name)


class Audit(Base, LastModifiedMixin):
	""" An audit, belongs to an event. 
	"""
	__tablename__ = 'audits'
	
	id = Column(Integer, primary_key=True)

	active = Column(Boolean(), default=True)

	event_id = Column(Integer, ForeignKey('events.id'))
	event = relationship(Event, backref=backref('audits', order_by=id))
	
	location_id = Column(Integer, ForeignKey('locations.id'))
	location = relationship(Location, backref=backref('audits', order_by=id))

	starts = Column(DateTime())
	ends = Column(DateTime())
	
	def __init__(self, active=False, event=None, location=None,
		starts=None, ends=None):
		self.active = active
		self.event = event
		if event:
			self.event_id = event.id
		self.location = location
		if location:
			self.location_id = location.id
		self.starts = starts
		self.ends = ends

	def __repr__(self):
		return u'{:%d.%m.%Y %H:%M}'.format(self.starts) # , self.location.name)
		# return u'{0}'.format(self.seat_stats()) # , self.location.name)
	
	def total_seats(self):
		return self.location.capacity
	
	def available_seats(self):
		return self.location.capacity - len(Enrollment.query.filter(Enrollment.audit==self).all())
		
	def seat_stats(self):
		return u'{0}/{1}'.format(self.available_seats(), self.total_seats())

class Enrollment(Base, LastModifiedMixin):
	""" Users and Audits. 
	"""
	__tablename__ = 'enrollments'
	
	id = Column(Integer, primary_key=True)
	
	audit_id = Column(Integer, ForeignKey('audits.id'))
	audit = relationship(Audit, backref=backref('enrollments', order_by=id))

	user_id = Column(Integer, ForeignKey('users.id'))
	user = relationship(User, backref=backref('enrollments', order_by=id))
	
	enrollment_date = Column(DateTime())
	subjects = Column(UnicodeText())
	
	def __init__(self, audit=None, user=None, enrollment_date=None,
		subjects=None):
		self.audit = audit
		if audit:
			self.audit_id = audit.id
		self.user = user
		if user:
			self.user_id = user.id
		if not enrollment_date:
			self.enrollment_date = datetime.datetime.now()
		self.subjects = subjects

	def __repr__(self):
		return u'<Enrollment {0} for {1}>'.format(self.user.email, self.audit)
