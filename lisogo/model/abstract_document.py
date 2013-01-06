# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

import abc
from inspect import getmembers, ismethod
from lisogo.model.exceptions import *
from pymongo import collection as pymongo_collection

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
    not methods, not in the list of :prop:`_ignoredFields` and not starting
    by an underscore `_`. The only exception to this rule is the property
    `_id`, which is used to store the document identifier from mongodb.
    A custom `_type` field is added to the son representation, containing the
    class name of `self`.

    :meth:`fromSON` is the reverse operation, it populates the object's members
    with those in the dictionary.

    Nested documents and references are not yet supported (but will come soon,
    I guess).
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """
        Constructs the document.

        Sets an empty _id field and default value for metadata.

        :prop:`_ignoredFields` In concrete implementations of a document, it
        is possible to ignore fields when converting the object in SON by
        appending property names to the list.
        """
        object.__setattr__(self, '_id', None)
        object.__setattr__(self, '_modified', False)
        object.__setattr__(self, '_ignoredFields', ['id', 'modified'])

    def _invalidateFieldsCache(self):
        """
        Invalidate the cache of field values.
        """
        try:
            del self._fields
        except AttributeError:
            pass

    def attributeModified(self, attribute, value):
        """
        Returns wether setting the value `value` to the object's attribute
        `attribute` will modify the current object SON representation.

        If the attribute is modified, the internal field caches are updated.
        """
        try:
            modified = self.__dict__[attribute] != value

            if modified:
                self._invalidateFieldsCache()

            return modified and attribute in self.fieldnamesToStore()
        except KeyError:
            try:
                return self.__getattr__(attribute) != value
            except AttributeError:
                # We added a new attribute, invalidate the cache of fields if
                # defined
                self._invalidateFieldsCache()

                try:
                    del self._fieldnames
                except AttributeError:
                    pass

                return True

    def __setattr__(self, attribute, value):
        """
        Intercepts and redispatch attributes set operations in order to check
        if the document have been modified.
        """
        if not self.ignoreMember(attribute):
            object.__setattr__(self, '_modified', self.attributeModified(attribute, value))

        return object.__setattr__(self, attribute, value)

    @property
    def modified(self):
        """
        Tells if the current object has been modified since the last time
        :meth:`fromSON()` or :meth:`save()` have been called.

        If the object is new, if no property that would appear in the SON
        representation has been set, the object is not modified.
        """
        return self._modified

    @property
    def id(self):
        """
        Returns the id of the document, or `None` if the document has not been
        persisted yet.

        id is a property.
        """
        return self._id

    def ignoreMember(self, member):
        """
        Returns true if the memeber member should be ignored when creating the
        SON representation of the object.

        :param member: tuple (member name, member value)
        """
        return member[0][0] == '_' or member[0] in self._ignoredFields \
                or ismethod(member[1])

    def fieldsToStore(self):
        """
        Returns the list of fields of the current object that have to be
        exported by toSON.
        """
        try:
            return self._fields
        except AttributeError:
            self._fields = [member for member in getmembers(self)
                    if not self.ignoreMember(member)]

            return self._fields

    def fieldnamesToStore(self):
        """
        Return as a list the name of each field in the current object that have
        to be exported by toSON.
        """
        try:
            return self._fieldnames
        except AttributeError:
            self._fieldnames = [member[0] for member in getmembers(self)
                    if not self.ignoreMember(member)]

            return self._fieldnames

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
        a collection. Such a situation will raise a :class:`PersistError`.

        The method will not try to save a document that is not marked as
        modified (by :prop:`modified`).

        Returns the object for fluent API.

        The id of the document will be set according to the value returned by
        pymongo.

        :param db: mongodb database object
        """
        if not self.modified:
            return self

        collection = self.collection(db)

        if not collection:
            raise PersistError("The object of type %s can only be nested" \
                " (no collection defined)" % self.__class__.__name__)

        self._id = collection.save(self)

        object.__setattr__(self, '_modified', False)

        return self

    def retrieve(self, spec_or_id, db):
        """
        Retrieves the document in the collection returned by
        :meth:`collection`. If the document is found, it will populate the
        current object, else, :class:`NotFoundError` will be raised.

        If collection returns ``None``, it means that the document can not be
        retrieved on its own and is nested in a parent document. Such
        a situation will raise a :class:`RetrieveError`.

        :param spec_or_id: dictionary with at least an `_id` field or any other
        value licit value for the field "_id". The value can be
        a `pymongo.ObjectId` object or a value that can be converted in
        `ObjectId`.

        :param db: mongodb database object
        """
        collection = self.collection(db)

        if not collection:
            raise RetrieveError("The object of type %s can only be " \
                    "nested (no collection defined)" % self.__class__.__name__)

        if isinstance(spec_or_id, dict):
            if "_id" not in spec_or_id:
                raise RetrieveError('"spec_or_id" as a dict must have ' \
                        'an "_id" field.')
        else:
            spec_or_id = {"_id": spec_or_id}

        # We use the original pymongo.collection.Collection class definition to
        # be sure to get the original dict object.
        found = None
        for item in pymongo_collection.Collection.find(collection, spec_or_id).limit(-1):
            found = item

        if not found:
            raise NotFoundError("No object with id %s in %s's collection"
                    % (spec_or_id["_id"], self.__class__.__name__))

        self.fromSON(found)

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
            # ignore the fields containing types metadata
            if key == '_type' or key == '_types_mapping':
                continue

            self.__dict__[key] = son[key]

        object.__setattr__(self, '_modified', False)


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

        for member in self.fieldsToStore():
            son[member[0]] = member[1]

        son['_type'] = self.__class__.__name__

        return son
