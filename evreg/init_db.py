# -*- coding: utf-8 -*-

from database import init_db, db_session
from models import User, Group, Location, Event
from werkzeug import generate_password_hash
import datetime

init_db()
session = db_session()

user = User(
	username='martin.czygan@gmail.com',
	first_name='Martin',
	last_name='Czygan',
	dob=datetime.datetime(1979, 4, 29),
	email='martin.czygan@gmail.com', 
	identifier_id='0000',
	city='Leipzig',
	country='DEU',
	zipcode='04277',
	street='Brandstr. 15',
	password=generate_password_hash('dev')
)

group = Group(name='admin')
user.groups.append(group)

session.add(user)
session.add(group)
session.commit()

location = Location()