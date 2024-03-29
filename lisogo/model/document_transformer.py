# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from pymongo.son_manipulator import SONManipulator
from bson.objectid import ObjectId
from lisogo.model import abstract_document, document_placeholder

class DocumentTransformer(SONManipulator):
    """
    The `DocumentTransformer` has the responsability to transform our model
    objects into nested structures or references to objects that can be stored
    and manipulated by mongodb, using pymongo.

    You might want to read about this feature of pymongo on the following
    links:

      * http://api.mongodb.org/python/current/examples/custom_type.html
      * http://api.mongodb.org/python/current/api/pymongo/son_manipulator.html

    .. note:: :clas::`SONManipulator` instances are not supposed to deal with
    anything that is not a dict, and it is a prerequisite of the pymongo
    library. Therefore, the :class:`DocumentTransformer` will only deal with
    nested objects in a dictionary, and not work on the object at the first
    level.
    """

    def __init__(self, module = 'lisogo.model'):
        SONManipulator.__init__(self)
        self.module = module

    def transform_incoming(self, son, collection):
        """
        Manipulates a SON object to be stored in the database.

        This method transforms :class:`abstract_document.AbstractDocument`
        instances into dictionaries that can be stored by mongodb, recursively.

        Nested documents are transformed and simply nested when they don't
        provide a collection to store them in
        (:meth:`abstract_document.AbstractDocument.collection`).

        Nested documents with a collection are stored and represented has
        references, using :class:`ObjectId` (form `bson`).

        :param son: the SON object to be inserted into the database
        :param collection: the collection the object is being inserted into
        """
        types_mapping = {}

        for (key, value) in son.items():
            # Traverse nested dictionaries recursively
            if isinstance(value, dict):
                son[key] = self.transform_incoming(value, collection)

            # Not an abstract document, nothing to do here
            if not isinstance(value, abstract_document.AbstractDocument):
                continue

            # Is it a document to reference or to store nested?
            if collection and value.collection(collection.database):
                # Save the document and use it as a reference
                value.save(collection.database)
                son[key] = value.id

                # Store the type of the referenced object as we'll need it when
                # doing the reverse operation
                types_mapping[str(value.id)] = value.__class__.__name__
            else:
                # Serialize the nested document
                son[key] = value.toSON()

        if types_mapping:
            son['_types_mapping'] = types_mapping

        return son

    def transform_outgoing(self, son, collection):
        """
        Transforms the SON object fetched from the database.

        Dictionaries with a field named `_type` will be transformed into the
        matching :class:`abstract_document.AbstractDocument` concrete
        implementation, recursively.

        Nested documents (sub-dictionaries) are also transformed into plain
        python objects if they follow the same guidelines.

        It is important to note that the behavior with nested references change
        whether lazy loading is enabled or not. When nested documents are
        fetched eagerly, the method used is :meth:`AbstractDocument.retrieve()`
        which does not use the cache and guarantee that the document will be
        returned as it is known in the database.

        However, lazy loading's :class:`DocumentPlaceholder` leverages the
        cache feature if enabled. This behavior is consistent with the intent
        of lazy loading in term of performance optimization.

        :param son: the SON object being retrieved from the database
        :param collection: the collection this object was stored in
        """
        for (key, value) in son.items():
            if isinstance(value, ObjectId):
                try:
                    doctype = son['_types_mapping'][str(value)]
                    document = self._create_document_from_doctype(doctype)

                    if collection.database.lazy_loading_is_enabled:
                        placeholder = document_placeholder.DocumentPlaceholder(
                            document.collection(collection.database), value)
                        son[key] = placeholder
                    else:
                        document.retrieve(value, collection.database)
                        son[key] = document
                except KeyError:
                    # No type mapping available, keep the object reference as
                    # it is, since there is nothing else to do. I could have
                    # choose to raise an exception, but it would forbid a user
                    # to use ObjectId values that are not handled by us.
                    pass

            elif isinstance(value, dict):
                if '_type' in value:
                    # This is a document we can handle
                    doctype = value['_type']
                    # TODO Maybe we should ignore importation errors and keep
                    # the serialized document
                    document = self._create_document_from_doctype(doctype)
                    document.fromSON(value)
                    son[key] = document
                else:
                    # An other kind of dictionary, transform it recursively
                    son[key] = self.transform_outgoing(value, collection)

        return son

    def _create_document_from_doctype(self, doctype):
        """
        Creates an empty document of the type defined by :param:`doctype`.

        :param doctype: string representation of a type, member of the module
        defined at the creation of the transformer.
        """
        if isinstance(doctype, unicode):
            doctype = doctype.encode('ascii', 'ignore')

        module = __import__(self.module, fromlist = [doctype])
        document = getattr(module, doctype)()

        return document
