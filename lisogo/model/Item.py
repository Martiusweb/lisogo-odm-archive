# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

import AbstractDocument

class Item(AbstractDocument):
	"""
	An `Item` object reprensents an item of a list.

	:param title: Title of the item, must be kept short

	:param description: Detailed description of the item
	"""
	title = ''

	description = ''

	def collection(self, db):
	    return db.items
