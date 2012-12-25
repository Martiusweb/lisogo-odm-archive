# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from pymongo.son_manipulator import SONManipulator
from lisogo.model import AbstractDocument

class DocumentTransformer(SONManipulator):
    """
    The `DocumentTransformer` has the responsability to transform our model
    objects into nested structures or references to objects that can be stored
    and manipulated by mongodb, using pymongo.

    You might want to read about this feature of pymongo on the following
    links:

      * http://api.mongodb.org/python/current/examples/custom_type.html
      * http://api.mongodb.org/python/current/api/pymongo/son_manipulator.html

    TODO It is probably required to check if this transformer should handle
    or not the son reprensentation that are given to him, like if other
    transformers might also act.

    TODO A good thing to do would be to be able to fetch references lazily.
    """

    def __init__(self, module = 'lisogo.model'):
        SONManipulator.__init__(self)
        self.module = module

    def transform_incoming(self, son, collection):
        """
        Manipulates a SON object to be stored in the database.

        This method transforms `AbstractDocument` instances into dictionaries
        that can be stored by mongodb, recursively.

        Nested documents are transformed and simply nested when they don't
        provide a collection to store them in
        (:meth:`AbstractDocument.collection`).

        Nested documents with a collection are stored and represented has
        references, using :class:`ObjectId` (form pymongo).

        :param son: the SON object to be inserted into the database
        :param collection: the collection the object is being inserted into
        """
        for (key, value) in son.items():
            # Traverse nested dictionaries recursively
            if isinstance(value, dict):
                son[key] = self.transform_incoming(value, collection)

            # Not an abstract document, nothing to do here
            if not isinstance(value, AbstractDocument):
                continue

            # Is it a document to reference or to store nested?
            if collection and value.collection(collection.database):
                # Save the document and use it as a reference
                value.save(collection.database)
                son[key] = value.id
            else:
                # Serialize the nested document
                son[key] = value.toSON()

        return son

    def transform_outgoing(self, son, collection):
        """
        Transforms the SON object fetched from the database.

        Dictionaries with a field named `_type` will be transformed into the
        matching `AbstractDocument` concrete implementation, recursively.

        Nested documents (sub-dictionaries) are also transformed into plain
        python objects if they follow the same guidelines.

        TODO: References are replaced by the corresponding python object.

        :param son: the SON object being retrieved from the database
        :param collection: the collection this object was stored in
        """
        for (key, value) in son.items():
            if isinstance(value, dict):
                if '_type' in value:
                    # This is a document we can handle
                    doctype = value['_type']
                    if isinstance(doctype, unicode):
                        doctype = doctype.encode('ascii', 'ignore')
                    module = __import__(self.module, fromlist = [doctype])
                    document = getattr(module, doctype)()
                    document.fromSON(value)
                    son[key] = document
                else:
                    # An other kind of dictionary, transform it recursively
                    son[key] = self.transform_outgoing(value, collection)

        return son
