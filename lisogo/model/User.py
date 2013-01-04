# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from lisogo.model import abstract_document

class User(abstract_document.AbstractDocument):
	"""
	An `User` object reprensents an identified user on lisogo.

	The user defines a list of goals he plans to achieve These goals are called
	objectives, and are objects associated to an `Item`.

	An objective is personal whereas an item can be shared by several users.

	:param name: Complete name of the user

	:param username: Name of the user as displayed

	:param email: Email address of the user
	"""

	name = ''

	username = ''

	email = ''

	def collection(self, db):
	    return db.users

	def getName(self):
	    return self.name

	def setName(self, name):
	    self.name = name
	    return self

	def getUsername(self):
	    return self.username

	def setUsername(self, username):
	    self.username = username
	    return self

	def getEmail(self):
	    return self.email

	def setEmail(self, email):
	    self.email = email
	    return self
