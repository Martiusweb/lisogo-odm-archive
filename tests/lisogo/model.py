# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from unittest import TestCase, TestLoader
from pymongo import MongoClient
from bson.objectid import ObjectId
from tests import config
from lisogo.model import AbstractDocument, DocumentTransformer, mongo_client, \
    object_cache
from lisogo.model.mongo_client import connect, select_db, Collection
from lisogo.model.exceptions import *

# Stub classes
class ConcreteDocument(AbstractDocument):
    def __init__(self, foo = '', bar = ''):
        AbstractDocument.__init__(self)

        self.foo = foo
        self.bar = bar

        self._ignoredField = 'Ignored value'

    def __eq__(self, other):
        return self.foo == other.foo and self.bar == other.bar

    def __repr__(self):
        return "(%s, %s)" % (self.foo, self.bar)

    def collection(self, db):
        return db.concrete_collection

    def getFoo(self):
        return self.foo

    def setFoo(self, foo):
        self.foo = foo
        return self

    def getBar(self):
        return self.bar

    def setBar(self, bar):
        self.bar = bar
        return self

class AnotherConcrete(AbstractDocument):
    def __init__(self, foo = ''):
        AbstractDocument.__init__(self)

        self.foo = foo

    def collection(self, db):
        return db.another_concrete

    def getFoo(self):
        return self.foo

    def setFoo(self, foo):
        self.foo = foo
        return self

# Basic tests of AbstractDocument
class AbstractDocumentTest(TestCase):
    def test_initWithEmptyId(self):
        doc = ConcreteDocument()
        self.assertIsNone(doc.id)

    def test_toSONHasRequiredFields(self):
        foo = 'foo value'
        bar = 'bar value'
        doc = ConcreteDocument(foo, bar)
        son = doc.toSON()

        self.assertTrue('foo' in son)
        self.assertTrue('bar' in son)

        self.assertEqual(son['foo'], foo)
        self.assertEqual(son['bar'], bar)

    def test_toSONIgnoresUnderscoreAndIgnoredMembers(self):
        doc = ConcreteDocument('foo', 'bar')
        son = doc.toSON()

        self.assertFalse('_ignoredField' in son)

        self.assertEqual(len(son), 3)

    def test_toSONIncludesType(self):
        doc = ConcreteDocument('foo', 'bar')
        son = doc.toSON()

        self.assertTrue('_type' in son)
        self.assertEqual(son['_type'], doc.__class__.__name__)

    def test_idOfNewDocIsNone(self):
        doc = ConcreteDocument('foo', 'bar')

        self.assertEqual(doc.id, None)

    def test_fromSonChecksType(self):
        doc1 = ConcreteDocument('foo', 'bar')
        doc2 = AnotherConcrete()

        son2 = doc2.toSON()

        with self.assertRaises(AssertionError):
            doc1.fromSON(son2)

        del son2['_type']

        with self.assertRaises(KeyError):
            doc2.fromSON(son2)

    def test_toSONIgnoresEmptyId(self):
        doc = ConcreteDocument('foo', 'bar')
        son = doc.toSON()

        self.assertFalse('_id' in son)

    def test_toSONIncludesIdIfDefined(self):
        doc = ConcreteDocument('foo', 'bar')
        doc._id = 'foo'

        son = doc.toSON()

        self.assertTrue(son['_id'], 'foo')

    def test_fromSONIncludesIdIfDefined(self):
        an_id = "anId"
        son = {"foo": "foo", "bar": "bar", "_id": an_id,
                "_type": "ConcreteDocument"}

        doc = ConcreteDocument()
        doc.fromSON(son)

        self.assertEqual(doc.id, an_id)

    def test_fromSONIgnoresType(self):
        son = {"foo": "foo", "bar": "bar", "_type": "ConcreteDocument"}

        doc = ConcreteDocument()
        doc.fromSON(son)

        self.assertFalse("_type" in doc.__dict__)

    def test_emptyDocumentNotModified(self):
        class ConcreteEmpty(AbstractDocument):
            def __init__(self):
                AbstractDocument.__init__(self)

            def collection(self, db):
                return None

        doc = ConcreteEmpty()

        self.assertFalse(doc.modified)

    def test_newDocumentIsModified(self):
        doc = ConcreteDocument('foo', 'bar')

        self.assertTrue(doc.modified)

    def test_notModifiedCases(self):
        son = {"foo": "foo", "bar": "bar", "_type": "ConcreteDocument"}
        doc = ConcreteDocument()
        doc.fromSON(son)

        self.assertFalse(doc.modified)

        doc._ignoredField = 'changed'
        self.assertFalse(doc.modified)

        doc.setFoo(son["foo"])
        self.assertFalse(doc.modified)

    def test_modifiedAfterFromSONIsModified(self):
        son = {"foo": "foo", "bar": "bar", "_type": "ConcreteDocument"}
        doc = ConcreteDocument()
        doc.fromSON(son)

        doc.foo = 'other value'

        self.assertTrue(doc.modified)

# Tests requiring an access to mongodb
class AbstractStorageTest(TestCase):
    def setUp(self):
        self.con = connect(config.MONGODB_HOST, config.MONGODB_PORT)
        self.db = select_db(self.con, config.MONGODB_DB_NAME, 'tests.lisogo.model')

    def tearDown(self):
        self.db = None
        self.con.drop_database(config.MONGODB_DB_NAME)
        self.con.disconnect()
        self.con = None

class AbstractDocumentStorageTest(AbstractStorageTest):
    def test_save(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)
        result = doc.save(self.db)

        self.assertEqual(result, doc)

        doc_id = doc.id
        self.assertIsNotNone(doc_id)

        other = collection.find_one({"_id": doc_id})

        self.assertEqual(other.id, doc.id)
        self.assertEqual(other.getFoo(), doc.getFoo())
        self.assertEqual(other.getBar(), doc.getBar())

    def test_afterSaveIsNotModified(self):
        doc = ConcreteDocument('foo', 'bar')
        doc.save(self.db)

        self.assertFalse(doc.modified)

    def test_retrieve(self):
        doc = ConcreteDocument('hello', 'world')
        doc.save(self.db)

        new_doc = ConcreteDocument()
        new_doc.retrieve(doc.id, self.db)

        self.assertEqual(new_doc, doc)

        del new_doc
        new_doc = ConcreteDocument()
        new_doc.retrieve({"_id": doc.id}, self.db)
        self.assertEqual(new_doc, doc)

    def test_retrieveRaiseExceptionWhenIdIsMissing(self):
        doc = ConcreteDocument()

        with self.assertRaises(RetrieveError):
            doc.retrieve({"useless_field": "useless value"}, self.db)

    def test_retrieveNonExistingRaiseNotFound(self):
        doc = ConcreteDocument()
        # ensure the query won't return an object
        doc.collection(self.db).remove({"_id": "not_existing"})

        with self.assertRaises(NotFoundError):
            doc.retrieve("not_existing", self.db)

# Test the behavior of the Abc
class AbstractDocumentAbcTest(TestCase):
    def test_abstractMethodMustBeImplemented(self):
        class IncompleteConcrete(AbstractDocument):
            pass

        with self.assertRaises(TypeError):
            doc = IncompleteConcrete()

# Nested documents
class NestedDocument(AbstractDocument):
    def __init__(self, foo = ''):
        AbstractDocument.__init__(self)

        self.foo = foo

    def collection(self, db):
        return None

    def __eq__(self, other):
        return self.foo == other.foo

class DocumentWithNested(AbstractDocument):
    def __init__(self, data = '', nested = None):
        AbstractDocument.__init__(self)

        self.data = data

        self.nested = nested

    def setNested(self, nested):
        self.nested = nested
        return self

    def getNested(self):
        return self.nested

    def collection(self, db):
        return db.document_with_nested

    def __eq__(self, other):
        return self.data == other.data and self.nested == other.nested

class SaveNestedDocumentTest(AbstractStorageTest):
    def test_saveRaiseExceptionWhenNested(self):
        doc = NestedDocument('foo')

        with self.assertRaises(PersistError):
            # I can provide None instead of a valid access to a database since
            # an exception should be raised before trying to access mongodb in
            # any way.
            doc.save(None)

    def test_retrieveRaiseExceptionWhenNested(self):
        doc = NestedDocument('foo')

        with self.assertRaises(RetrieveError):
            doc.retrieve('dummy id', None)

    def test_saveDocumentWithNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        collection = doc.collection(self.db)
        count_before_save = collection.count()

        result = doc.save(self.db)

        self.assertEqual(result, doc)
        self.assertEqual(collection.count(), count_before_save+1)

    def test_findDocumentWithNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        doc.save(self.db)

        collection = doc.collection(self.db)

        retrieved_doc = collection.find_one({"_id": doc._id})

        self.assertEqual(retrieved_doc.getNested(), doc.getNested())
        self.assertEqual(retrieved_doc, doc)

    def test_saveDocumentWithReferenceToNewObject(self):
        nested = ConcreteDocument('foo', 'bar')
        doc = DocumentWithNested('foo', nested)

        doc_collection = doc.collection(self.db)
        nested_collection = nested.collection(self.db)

        doc_count = doc_collection.count()
        nested_count = doc_collection.count()

        result = doc.save(self.db)

        self.assertEqual(result, doc)
        self.assertIsNotNone(doc.id)
        self.assertIsNotNone(nested.id)
        self.assertEqual(doc_collection.count(), doc_count+1)
        self.assertEqual(nested_collection.count(), nested_count+1)

    def test_RetrieveDocumentWithReferenceToObject(self):
        nested = ConcreteDocument('foo', 'bar')
        doc = DocumentWithNested('foo', nested)

        doc.save(self.db)

        other_doc = DocumentWithNested()
        other_doc.retrieve(doc.id, self.db)

        self.assertEqual(other_doc, doc)
        self.assertEqual(other_doc.nested, nested)

class DocumentTransformerTest(TestCase):
    def setUp(self):
        self.transformer = DocumentTransformer('tests.lisogo.model')

    def test_DocumentTransformerIncomingForSimpleDocument(self):
        doc = ConcreteDocument('foo', 'bar')
        son = doc.toSON()

        transformed = self.transformer.transform_incoming(son.copy(), None)
        self.assertEqual(transformed, son)

    def test_DocumentTransformerIncomingForNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        son = doc.toSON()
        nested_son = doc.nested.toSON()

        transformed = self.transformer.transform_incoming(son.copy(), None)

        self.assertEqual(transformed['data'], son['data'])
        self.assertEqual(transformed['nested'], nested_son)

    def test_DocumentTransformerOutgoingForSimpleDocument(self):
        doc = ConcreteDocument('foo', 'bar')
        son = doc.toSON()

        transformed = self.transformer.transform_incoming(son.copy(), None)
        back = self.transformer.transform_outgoing(transformed.copy(), None)

        self.assertEqual(back, son)

    def test_DocumentTransformerOutgoingForNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        son = doc.toSON()

        transformed = self.transformer.transform_incoming(son.copy(), None)
        back = self.transformer.transform_outgoing(transformed.copy(), None)

        self.assertEqual(back['nested'], son['nested'])

class MongoClientTest(AbstractStorageTest):
    def setUp(self):
        super(MongoClientTest, self).setUp()
        self.db.disable_cache()

    def test_DatabaseReturnsCollectionObjects(self):
        collection = self.db.a_collection_for_this_test
        self.assertIsInstance(collection, mongo_client.Collection)
        collection.drop()

        collection = self.db['a_collection_for_this_test']
        self.assertIsInstance(collection, mongo_client.Collection)
        collection.drop()

        collection = self.db.create_collection('a_collection_for_this_test')
        self.assertIsInstance(collection, mongo_client.Collection)
        collection.drop()

    def test_saveInCollection(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)

        doc_id = collection.save(doc)
        self.assertIsNotNone(doc.id)

        other_doc = ConcreteDocument()
        other_doc.retrieve({'_id': doc_id}, self.db)

        self.assertEqual(doc, other_doc)

    def test_insertInCollection(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)

        doc_id = collection.insert(doc)
        self.assertIsNotNone(doc.id)

        other_doc = ConcreteDocument()
        other_doc.retrieve({'_id': doc_id}, self.db)

        self.assertEqual(doc, other_doc)

    def test_insertListInCollection(self):
        doc1 = ConcreteDocument('doc', 'no1')
        doc2 = ConcreteDocument('doc', 'no2')

        collection = doc1.collection(self.db)
        collection.insert([doc1, doc2])

        self.assertIsNotNone(doc1.id)
        self.assertIsNotNone(doc2.id)

        other_doc1 = ConcreteDocument()
        other_doc1.retrieve({'_id': doc1.id}, self.db)
        other_doc2 = ConcreteDocument()
        other_doc2.retrieve({'_id': doc2.id}, self.db)

        self.assertEqual(doc1, other_doc1)
        self.assertEqual(doc2, other_doc2)


    def test_updateInCollection(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)
        doc_id = collection.insert(doc)

        doc.setFoo('coucou foo')
        collection.update({'_id': doc_id}, doc)

        other_doc = ConcreteDocument()
        other_doc.retrieve({'_id': doc_id}, self.db)

        self.assertEqual(doc.getFoo(), other_doc.getFoo())
        self.assertEqual(doc, other_doc)

    def test_find(self):
        doc = ConcreteDocument('foo', 'bar')
        doc.save(self.db)
        collection = doc.collection(self.db)

        found_doc = collection.find_one({'_id': doc.id})

        self.assertEqual(found_doc, doc)

        doc2 = ConcreteDocument('foo', 'baz')
        doc2.save(self.db)

        docs_found = [None, None]
        for found in collection.find({'foo': 'foo'}):
            if found.id == doc.id:
                docs_found[0] = found
            elif found.id == doc2.id:
                docs_found[1] = found

        self.assertEqual(docs_found[0], doc)
        self.assertEqual(docs_found[1], doc2)

class ObjectCacheTest(TestCase):
    def setUp(self):
        self.object = object_cache.ObjectCache()
        self.foo = ObjectId()

    def tearDown(self):
        self.object = None

    def test_defaultIsEnabledEmpty(self):
        self.assertTrue(self.object.is_enabled)
        self.assertEqual(len(self.object), 0)

    def test_disableAtConstruction(self):
        o = object_cache.ObjectCache(False)
        self.assertFalse(o.is_enabled)

    def test_standardDictBehavior(self):
        if self.foo in self.object:
            del self.object[self.foo]

        self.assertFalse(self.foo in self.object)

        length = len(self.object)
        self.object[self.foo] = 'bar'

        self.assertEqual(len(self.object), length+1)
        self.assertEqual(self.object[self.foo], 'bar')
        self.assertTrue(self.foo in self.object)

        del self.object[self.foo]

        self.assertFalse(self.foo in self.object)

    def test_whenDisabled(self):
        self.object[self.foo] = 'bar'

        self.object.is_enabled = False
        self.assertFalse(self.foo in self.object)
        self.assertEqual(len(self.object), 0)

        bar = ObjectId()
        self.object[bar] = 'foo'
        self.object.is_enabled = True
        self.assertFalse(bar in self.object)
        self.assertEqual(len(self.object), 1)

# TODO
class ObjectCacheCollectionTest(TestCase):
    def setUp(self):
        self.object = object_cache.ObjectCacheCollection()

    def tearDown(self):
        self.object = None

    def test_getAndsetCache(self):
        cache = object_cache.ObjectCache()
        self.object.set_cache('foo', cache)

        self.assertIs(self.object.get_cache('foo'), cache)

    def test_missingRaiseKeyError(self):
        cache = object_cache.ObjectCache()

        with self.assertRaises(KeyError):
            cache['does not exists']

    def test_enableCaches(self):
        cache = object_cache.ObjectCache(is_enabled = False)
        self.object.set_cache('foo', cache)
        self.object_cache.enable_caches()

        self.assertTrue(cache.is_enabled)

    def test_disableCaches(self):
        cache = object_cache.ObjectCache()
        self.object.set_cache('foo', cache)
        self.object.disable_caches()

        self.assertFalse(cache.is_enabled)

    def test_enableCaches(self):
        cache = object_cache.ObjectCache()
        doc_id = ObjectId()
        cache[doc_id] = 'foo'

        self.object.set_cache('foo', cache)

        self.object.clear_caches()

        self.assertEqual(len(cache), 0)

class DatabaseCacheTest(AbstractStorageTest):
    def test_defaultCacheIsEnabled(self):
        self.assertTrue(self.db.cache_is_enabled)

    def test_enableDisableCache(self):
        self.db.enable_cache()
        self.assertTrue(self.db.cache_is_enabled)

        self.db.disable_cache()
        self.assertFalse(self.db.cache_is_enabled)

        self.db.enable_cache()
        self.assertTrue(self.db.cache_is_enabled)

    def test_createCacheForCollection(self):
        self.db.enable_cache()

        collection = self.db.collection
        self.assertIsNotNone(collection.cache)
        collection.drop()

class CollectionCacheTest(AbstractStorageTest):
    def test_setCache(self):
        collection = self.db.collection

        cache = object_cache.ObjectCache()
        collection.set_cache(cache)

        self.assertIs(collection.cache, cache)
        collection.drop()

    def test_addInCacheOnSave(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)

        doc_id = collection.save(doc)

        self.assertIs(collection.cache[doc_id], doc)

    def test_addInCacheOnSaveNestedWithRef(self):
        nested_doc = ConcreteDocument('hello', 'world')
        doc = DocumentWithNested('what', nested_doc)

        doc.save(self.db)

        nested_collection = nested_doc.collection(self.db)
        self.assertIs(nested_collection.cache[nested_doc.id], nested_doc)
        self.assertIs(doc.collection(self.db).cache[doc.id], doc)

    def test_addInCacheOnInsertOne(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)

        doc_id = collection.insert(doc)

        self.assertIs(collection.cache[doc_id], doc)

    def test_addInCacheOnInsertSeveral(self):
        doc1 = ConcreteDocument('foo', 'bar')
        doc2 = ConcreteDocument('bar', 'baz')
        collection = doc1.collection(self.db)

        collection.insert([doc1, doc2])

        self.assertIs(collection.cache[doc1.id], doc1)
        self.assertIs(collection.cache[doc2.id], doc2)

    def test_addInCacheOnUpdate(self):
        doc = ConcreteDocument('foo', 'first')
        collection = doc.collection(self.db)

        self.db.disable_cache()
        doc_id = collection.insert(doc)
        self.db.enable_cache()

        doc.setBar('second')
        collection.update({"_id": doc_id}, doc)

        self.assertIs(collection.cache[doc_id], doc)

    def test_findReturnsCachedObjectIfIdIsInCache(self):
        doc = ConcreteDocument('foo', 'first')
        collection = doc.collection(self.db)

        doc_id = collection.insert(doc)

        for result in collection.find({'_id': doc_id}).limit(-1):
            self.assertIs(result, doc)

    def test_findReturnsCachedObjectAfterRetrieval(self):
        doc = ConcreteDocument('foo', 'bar')
        doc.save(self.db)
        collection = doc.collection(self.db)

        found_doc = collection.find_one({'_id': doc.id})

        self.assertEqual(found_doc, doc)

        doc2 = ConcreteDocument('foo', 'baz')
        doc2.save(self.db)

        docs_found = [None, None]
        for found in collection.find({'foo': 'foo'}):
            if found.id == doc.id:
                docs_found[0] = found
            elif found.id == doc2.id:
                docs_found[1] = found

        self.assertIs(docs_found[0], doc)
        self.assertIs(docs_found[1], doc2)

