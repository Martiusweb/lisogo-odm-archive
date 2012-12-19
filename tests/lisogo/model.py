# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from unittest import TestCase, TestLoader
from pymongo import MongoClient
from tests import config
from lisogo.model import AbstractDocument

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

class AbstractDocumentTest(TestCase):
    def setUp(self):
        self.con = MongoClient(config.MONGODB_HOST, config.MONGODB_PORT)
        self.db = self.con[config.MONGODB_DB_NAME]

    def tearDown(self):
        self.db.concrete_collection.drop()
        self.db = None
        self.con.drop_database(config.MONGODB_DB_NAME)
        self.con.disconnect()
        self.con = None

    def test_initWithEmptyId(self):
        doc = ConcreteDocument()
        self.assertIsNone(doc.id())

    def test_toSONHasRequiredFields(self):
        foo = 'foo value'
        bar = 'bar value'
        doc = ConcreteDocument(foo, bar)
        son = doc.toSON()

        self.assertTrue('foo' in son)
        self.assertTrue('bar' in son)

        self.assertEqual(son['foo'], foo)
        self.assertEqual(son['bar'], bar)

    def test_toSONIgnoresUnderscoreMembers(self):
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

        self.assertEqual(doc.id(), None)

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

        self.assertEqual(doc.id(), an_id)

    def test_fromSONIgnoresType(self):
        son = {"foo": "foo", "bar": "bar", "_type": "ConcreteDocument"}

        doc = ConcreteDocument()
        doc.fromSON(son)

        self.assertFalse("_type" in doc.__dict__)

    def test_save(self):
        doc = ConcreteDocument('foo', 'bar')
        collection = doc.collection(self.db)
        doc.save(self.db)

        doc_id = doc.id()
        self.assertIsNotNone(doc_id)

        son = collection.find_one({"_id": doc_id})
        other = ConcreteDocument('an', 'other')
        other.fromSON(son)

        self.assertEqual(other.id(), doc.id())
        self.assertEqual(other.getFoo(), doc.getFoo())
        self.assertEqual(other.getBar(), doc.getBar())

class AbstractDocumentAbcTest(TestCase):
    def test_abstractMethodMustBeImplemented(self):
        class IncompleteConcrete(AbstractDocument):
            pass

        with self.assertRaises(TypeError):
            doc = IncompleteConcrete()

