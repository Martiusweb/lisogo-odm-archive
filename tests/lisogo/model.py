# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from unittest import TestCase, TestLoader
from pymongo import MongoClient
from tests import config
from lisogo import mongodb_connect, mongodb_select_db
from lisogo.model import AbstractDocument, DocumentTransformer
from lisogo.model.exceptions import PersistException

# Stub classes
class ConcreteDocument(AbstractDocument):
    def __init__(self, foo = '', bar = ''):
        AbstractDocument.__init__(self)

        self.foo = foo
        self.bar = bar

        self._ignoredField = 'Ignored value'

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
        self.con = mongodb_connect(config.MONGODB_HOST, config.MONGODB_PORT)
        self.db = mongodb_select_db(self.con, config.MONGODB_DB_NAME, 'tests.lisogo.model')

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

        son = collection.find_one({"_id": doc_id})
        other = ConcreteDocument('an', 'other')
        other.fromSON(son)

        self.assertEqual(other.id, doc.id)
        self.assertEqual(other.getFoo(), doc.getFoo())
        self.assertEqual(other.getBar(), doc.getBar())

    def test_afterSaveIsNotModified(self):
        doc = ConcreteDocument('foo', 'bar')
        doc.save(self.db)

        self.assertFalse(doc.modified)

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

        with self.assertRaises(PersistException):
            # I can provide None instead of a valid access to a database since
            # an exception should be raisen before trying to access mongodb in
            # any way.
            doc.save(None)

    def test_SaveDocumentWithNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        collection = doc.collection(self.db)
        count_before_save = collection.count()

        result = doc.save(self.db)

        self.assertEqual(result, doc)
        self.assertEqual(collection.count(), count_before_save+1)

    def test_FindDocumentWithNestedDocument(self):
        doc = DocumentWithNested('foo', NestedDocument('bar'))
        doc.save(self.db)

        collection = doc.collection(self.db)

        retrieved = collection.find_one({"_id": doc._id})
        retrieved_doc = DocumentWithNested()
        retrieved_doc.fromSON(retrieved)

        self.assertEqual(retrieved['nested'], doc.nested)
        self.assertEqual(retrieved_doc, doc)

    def test_SaveDocumentWithReferenceToNewObject(self):
        nested = ConcreteDocument('foo', 'bar')
        doc = DocumentWithNested('foo', nested)

        doc_collection = doc.collection(self.db)
        nested_collection = nested.collection(self.db)

        doc_count = doc_collection.count()
        nested_count = doc_collection.count()

        result = doc.save(self.db)

        self.assertEqual(result, doc)
        self.assertEqual(doc_collection.count(), doc_count+1)
        self.assertEqual(nested_collection.count(), nested_count+1)

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
