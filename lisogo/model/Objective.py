# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from lisogo.model import abstract_document

class Objective(abstract_document.AbstractDocument):
	"""
	An `Objective` is a goal a users plan to achive or has achieved.

	A goal is associated to an `Item` object of the list.

	:param achieved: True if the user achieved this objective
	"""

	achieved = False

	def collection(self, db):
	    return db.objectives
