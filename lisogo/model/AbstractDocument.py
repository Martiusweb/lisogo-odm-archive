# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

import abc
from inspect import getmembers, ismethod
from exceptions import PersistException

class AbstractDocument(object):
    """
    An `AbstractDocument` represents an object that can be converted and stored
    as a document in a mongodb instance.

    This class is an Abc.

    You must override the method :meth:`collection`.

    The idea here is to provide a set of handful methods and helpers in order
    to persist objects in mongodb without spending much time working with an
    ODM.

    Currently, this class only support a first-level mapping between a
    dictionary and the object properties.

    :meth:`toSON` will insert into a dictionary the object members which are
    not methods, and not starting by an underscore `_`. The only exception to
    this rule is the property `_id`, which is used to store the document
    identifier from mongodb. A custom `_type` field is added to the son
    representation, containing the class name of `self`.

    :meth:`fromSON` is the reverse operation, it populates the object's members
    with those in the dictionary.

    Nested documents and references are not yet supported (but will come soon,
    I guess).
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """
        Constructs the document.

        Sets an empty _id field.
        """
        self._id = None

    def id(self):
        """
        Returns the id of the document, or `None` if the document has not been
        persisted yet.
        """
        return self._id

    def fields_to_store(self):
        """
        Returns the list of fields of the current object that have to be
        stored.
        """
        return [member for member in getmembers(self)
                if member[0][0] != '_' and not ismethod(member[1])]


    @abc.abstractmethod
    def collection(self, db):
        """
        Returns the mongodb collection in which objects are stored.

        If this method returns None, the object can only be stored has a nested
        object.

        :param db: mongodb database object
        """
        return None

    def save(self, db):
        """
        Saves the document in the collection returned by :meth:`collection`.

        If collection returns None, it means that the document can only be
        saved as a nested document, and therefore can not be stored in
        a collection. Such a situation will raise an Exception

        Returns the object for fluent API.

        The id of the document will be set according to the value returned by
        pymongo.

        :param db: mongodb database object
        """
        collection = self.collection(db)

        if not collection:
            raise PersistException("The object of type %s can only be nested" \
                " (no collection defined)" % self.__class__.__name__)

        self._id = collection.save(self.toSON())

        return self

    def fromSON(self, son):
        """
        Populates the object from a SON representation.

        An assertion will fail if the field `_type` of the son does not match
        the class name of `self`.

        :param son: the xSON representation of the object, in a dictionary.
        """
        assert son['_type'] == self.__class__.__name__

        for key in son:
            # ignore the type field
            if key == '_type':
                continue

            self.__dict__[key] = son[key]


    def toSON(self):
        """
        Builds a dictionary that is ready to be stored in mongo db.

        The current objects field starting with an underscore are ignored, with
        the exception of `_id`.

        An extra `_type` field will be added with the class name of `self`.
        """
        son = {}

        # ignore _id field if its value is None
        if self._id != None:
            son['_id'] = self._id

        for member in self.fields_to_store():
            son[member[0]] = member[1]

        son['_type'] = self.__class__.__name__

        return son
