# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

import pymongo
from lisogo.model import document_transformer
from lisogo.model import abstract_document
from lisogo.model import object_cache

class Cursor(pymongo.cursor.Cursor):
    _unique_already_returned = False

    """
    This class inherits from :class:`pymongo.cursor.Cursor` and decorates it
    with ODM features.

    If the documents returned by the cursor can be unserialized as instances of
    a model class, they will be returned unserialized.
    """
    def next(self):
        """
        Return the next element of the cursor, unserialized if possible.

        It will try to query the cache of the collection without performing
        a query to mongodb if:

          * `fields` is `None`
          * `spec` is defined for this cursor and contains and `_id`
          * `skip` is `0`

        If a query is performed and `fields` is `None`, the cache will be
        queried with the id of the document found instead of unserializing and
        issuing a new document object.
        """
        if not self.__fields and self.__skip == 0 and self.__spec:
            try:
                if self._unique_already_returned:
                    raise StopIteration

                document = self.__collection.cache[self.__spec['_id']]
                self._unique_already_returned = True
                return document
            except KeyError:
                # The spec does not have an '_id' or the element is not in cache
                pass

        document = super(Cursor, self).next()

        # Try using the cache
        if not self.__fields:
            try:
                return self.__collection.cache[document['_id']]
            except KeyError:
                # Element is not cached
                pass

        if not self.__manipulate:
            document = self.__collection._transform_outgoing_document(document)

        return self.__collection._unserialize(document)

class Collection(pymongo.collection.Collection):
    """
    This class inherits from :class:`pymongo.collection.Collection` and
    decorates it with ODM features.

    Documents retrieved through this class are python objects populated from
    the serialized version of the document stored in mongodb.

    Overriden methods are: :meth:`save`, :meth:`insert`, :meth:`update` and
    :meth:`find`.

    seealso:: `pymongo.collection.Collection` for the comprehensive
    documentation of this class.

    TODO It might be useful to offer some ODM features in a map-reduce context,
    I will investigate this later.
    """

    def __init__(self, database, name, create=False, **kwargs):
        """
        Create a mongo collection.

        seealso: :meth:`pymongo.collection.Collection` for the comprehensive
        documentation of this method.
        """
        super(Collection, self).__init__(database, name, create, **kwargs)

        self._cache = object_cache.ObjectCache(is_enabled = False)

    def set_cache(self, cache):
        """
        Set the :class:`ObjectCache` of this collection.

        The cache keeps one instance of the objects created or retrieved with
        this collection, allowing to manipulate only one instance of each
        document.
        """
        if not isinstance(cache, object_cache.ObjectCache):
            raise TypeError('Cache must be of type ObjectCache')

        self._cache = cache

    @property
    def cache(self):
        """
        Return the :class:`ObjectCache` object.
        """
        return self._cache

    def _serialize(self, document, manipulate):
        """
        Serialize the document.

        Internally, we use a :class:`pymongo.son_manipulator.SONManipulator`
        to serialize nested documents. If :param:`manipulate` is set to
        `False`, the manipulator will be explicitly called.

        :param document: document to serialize

        :param manipulate: set to `True` if the document will be manipulated by
        pymongo manipulators set for the database.
        """
        # If the object is an abstract document, we should transform it
        if isinstance(document, abstract_document.AbstractDocument):
            document = document.toSON()

            if not manipulate:
                document = self._transform_incoming_document(document)

        return document

    def _transform_incoming_document(self, document):
        """
        Apply to the
        :class:`lisogo.model.document_transformer.DocumentTransformer`
        manipulators to the document.

        :param document: Document to transform
        """
        for manipulator in self.database.incoming_manipulators:
            if not isinstance(manipulator, document_transformer.DocumentTransformer):
                continue

            document = manipulator.transform_incoming(document, self)

        return document

    def _unserialize(self, document):
        """
        Try to unserialize the document `document` into an instance of a model
        class.

        If the document does not have the required `_type` field, the document
        will be returned in its original serialized form.

        :param document: document to unserialize
        """
        # There is nothing we can do for this document, return it as it is.
        if '_type' not in document:
            return document

        manipulator = self.database._get_document_transformer()

        if manipulator:
            # We found a document_transformer.DocumentTransformer, we can
            # create an instance of the model and unserialize the document
            doctype = document['_type']
            instance = manipulator._create_document_from_doctype(doctype)
            instance.fromSON(document)
            document = instance

        return document

    def _transform_incoming_document(self, document):
        """
        Apply to the
        :class:`lisogo.model.document_transformer.DocumentTransformer`
        manipulators to the document.

        :param document: Document to transform
        """
        manipulator = self.database._get_document_transformer()

        if manipulator:
            document = manipulator.transform_outgoing(document, self)

        return document

    def save(self, to_save, manipulate=True, safe=None, check_keys=True,
            **kwargs):
        """
        Save a document in this collection.

        :class:`lisogo.model.abstract_document.AbstractDocument` instances will
        be serialized.

        Even if :param:`manipulate` is set to `False`, the
        :class:`document_transformer.DocumentTransformer` manipulators will be
        applied to the son object in order to serialize the object. Other
        manipulators will be ignored.

        seealso:: :meth:`pymongo.collection.Collection.save` for the
        comprehensive documentation of this method.
        """
        serialized = self._serialize(to_save, manipulate)

        result = super(Collection, self).save(serialized, manipulate, safe,
                check_keys, **kwargs)

        if result:
            to_save._id = result
            self._cache[result] = to_save

        return result

    def insert(self, doc_or_docs, manipulate=True, safe=None, check_keys=True,
            continue_on_error=False, **kwargs):
        """
        Insert (a) document(s) into this collection.

        :class:`lisogo.model.abstract_document.AbstractDocument` instances will
        be serialized.

        Even if :param:`manipulate` is set to `False`, the
        :class:`document_transformer.DocumentTransformer` manipulators will be
        applied to the son object in order to serialize the object. Other
        manipulators will be ignored.

        seealso:: :meth:`pymongo.collection.Collection.insert` for the
        comprehensive documentation of this method.
        """
        if isinstance(doc_or_docs, abstract_document.AbstractDocument):
            serialized = self._serialize(doc_or_docs, manipulate)
        elif not isinstance(doc_or_docs, dict):
            serialized = [self._serialize(doc, manipulate) for doc in doc_or_docs]
        else:
            serialized = doc_or_docs

        result = super(Collection, self).insert(serialized, manipulate,
                safe, check_keys, continue_on_error, **kwargs)

        if isinstance(result, list):
            for key in range(0, len(result)):
                if (result and
                    isinstance(doc_or_docs[key], abstract_document.AbstractDocument)):
                    doc_or_docs[key]._id = result[key]
                    self._cache[result[key]] = doc_or_docs[key]
        elif result and isinstance(doc_or_docs, abstract_document.AbstractDocument):
            doc_or_docs._id = result
            self._cache[result] = doc_or_docs

        return result

    def update(self, spec, document, upsert=False, manipulate=False, safe=None,
            multi=False, check_keys=True, **kwargs):
        """
        Update (a) document(s) in this collection.

        :class:`lisogo.model.abstract_document.AbstractDocument` instances will
        be serialized.

        Even if :param:`manipulate` is set to `False`, the
        :class:`document_transformer.DocumentTransformer` manipulators will be
        applied to the son object in order to serialize the object. Other
        manipulators will be ignored.

        seealso:: :meth:`pymongo.collection.Collection.update` for the
        comprehensive documentation of this method.
        """
        son = self._serialize(document, manipulate)

        result = super(Collection, self).update(spec, son, upsert,
                manipulate, safe, multi, check_keys, **kwargs)

        if result and 'err' in result and not result['err']:
            self._cache[document.id] = document

    def find(self, *args, **kwargs):
        """
        Query the database.

        If the document contains the required metadata, added by
        :meth:`lisogo.model.toSON`, the document will be unserialized and
        returned as an instance of the model class.

        seealso:: :meth:`pymongo.collection.Collection.find` for the
        comprehensive Documentation of this method.
        """
        if not 'slave_okay' in kwargs:
            kwargs['slave_okay'] = self.slave_okay
        if not 'read_preference' in kwargs:
            kwargs['read_preference'] = self.read_preference
        if not 'tag_sets' in kwargs:
            kwargs['tag_sets'] = self.tag_sets
        if not 'secondary_acceptable_latency_ms' in kwargs:
            kwargs['secondary_acceptable_latency_ms'] = (
                self.secondary_acceptable_latency_ms)

        cursor = Cursor(self, *args, **kwargs)
        return cursor

class Database(pymongo.database.Database):
    """
    This class inherits from :class:`pymongo.database.Database` and decorates it.

    The main feature that is added is the ODM feature: collections returned are
    also decorated, and are able to return python object from the serialized
    version stored in mongodb.

    The behavior of :class:`Database` or :class:`Collection` is undefined when
    several :class:`lisogo.model.document_transformer.DocumentTransformer` SON
    manipulators are added to the same database instance.

    By default, caching and lazy loading are enabled.

    seealso:: :class:`pymongo.database.Database` for the comprehensive
    documentation of this class.

    seealso:: :class:`Collection`
    """

    def __init__(self, connection, name):
        super(Database, self).__init__(connection, name)

        # Wether we want to enable ObjectCache
        self._cache_is_enabled = True

        # Wether we want to enable lazy loading
        self._lazy_loading_is_enabled = True

        # Collection of caches
        self._cache_collection = object_cache.ObjectCacheCollection()

    def enable_cache(self):
        """
        If the cache is not enabled, enables it from now.
        """
        if not self._cache_is_enabled:
            self._cache_is_enabled = True

            self._cache_collection.enable_caches()

    def disable_cache(self):
        """
        Disable every caches already existing.

        It does not clear the existing caches, but only disable them. If they
        are locally re-enabled, the objects already stored are still available.

        If the cache is re-enabled globally (from the database), the objects
        that are already cached are also still available.

        :class:`Collection` objects issued when the cache is disabled from the
        database will not get a cache.
        """
        if self._cache_is_enabled:
            self._cache_is_enabled = False

            self._cache_collection.disable_caches()

    def enable_lazy_loading(self):
        """
        Enable the lazy loading feature.

        Lazy loading is a feature that allow to retrieve nested documents
        referenced by their id only when the user will try to access them,
        minimizing the work done with the database.
        """
        self._lazy_loading_is_enabled = True

    def disable_lazy_loading(self):
        """
        Disable the lazy loading feature.

        Lazy loading will only be disabled from now. It means that documents
        already retrieved and/or in cache containing references to other
        documents will keep the lazy loading feature enabled.
        """
        self._lazy_loading_is_enabled = False

    @property
    def lazy_loading_is_enabled(self):
        return self._lazy_loading_is_enabled

    @property
    def cache_is_enabled(self):
        """
        Return `True` if the cache is enabled (the default), or `False`
        otherwise.

        cache_is_enabled is a property.
        """
        return self._cache_is_enabled

    def clear_cache(self):
        """
        Clears existing caches.
        """
        self._cache_collection.clear_caches()

    def __getattr__(self, name):
        """
        Get a collection of this database by name.

        Raises InvalidName if an invalid collection name is used.

        :param name: the name of the collection to get

        seealso:: :meth:`pymongo.Database.__getattr__`
        """
        if self._cache_is_enabled:
            collection = Collection(self, name)
            cache = self._cache_collection.get_cache(name, create_if_needed = True)
            collection.set_cache(cache)

            return collection
        else:
            return Collection(self, name)

    def create_collection(self, name, **kwargs):
        """
        Create a new :class:`Collection` in this database.

        seealso:: :meth:`pymongo.Database.create_collection`
        """
        opts = {"create": True}
        opts.update(kwargs)

        if name in self.collection_names():
            raise CollectionInvalid("collection %s already exists" % name)

        return self.__getattr__(name)

    def add_son_manipulator(self, manipulator):
        """
        Add a new son manipulator to this database.
        seealso:: :meth:`pymongo.Database.add_son_manipulator`
        """
        if isinstance(manipulator, document_transformer.DocumentTransformer):
            self._document_transformer = manipulator

        super(Database, self).add_son_manipulator(manipulator)

    def _get_document_transformer(self):
        return self._document_transformer

def connect(host = 'localhost', port = 27017):
    """
    Return an instance of :class:`pymongo.MongoClient`, dealing with the
    connection to a mongo node.

    :param host: mongo node host address, the default value is `localhost`

    :param port: mongo node host port, the default value is 27017, which is the
    default mongodb port
    """
    return pymongo.MongoClient(host, port)

def select_db(client, db_name, module):
    """
    Return an instance of  :class:`pymongo.Database` object.

    TODO Create instead an instance of :class:`lisogo.model.Database`,
    a decorated :class:`pymongo.Database` object.

    :param client: Mongo client object

    :param db_name: Name of the database to access

    :param module: absolute path of the module from which import model classes.
    This parameter must be defined in order to use the implicit and automatic
    translation from serialized objects to python class defined in the
    application.
    """
    db = Database(client, db_name)
    db.add_son_manipulator(document_transformer.DocumentTransformer(module))
    return db
