# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

class DocumentPlaceholder:
    """
    A `DocumentPlaceholder` objects acts as a placeholder for a document. It
    stores everything that is required in order to query and find a given
    document (collection object, document id, etc).

    It allows, for instance, to :class:`AbstractDocument` to lazyload an
    object, and retrieve it from the database only when the user will require
    it.
    """
    def __init__(self, collection, id):
        """
        Initialize a placeholder with the objects required to retrieve the
        object.
        """
        self._collection = collection
        self._id = id

    def find(self):
        return self._collection.find_one(self._id)

