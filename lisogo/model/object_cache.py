# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

import collections
from bson.objectid import ObjectId

class ObjectCache(collections.MutableMapping):
    """
    The :class:`ObjectCache` class allows to store and retrieve objects
    indexed by an object as unique identifier.

    It acts as a dictionary.

    If the object cache is disabled, no new object will be stored and will
    always return `None` when queried. The operator `in` will also return
    `False`.

    :param is_enabled: Whether the object cache should store and return objects
    or not.
    """
    def __init__(self, is_enabled = True):
        """
        Initialize the object cache.

        :param is_enabled: If `True`, the cache is enabled by default.
        """
        self.is_enabled = is_enabled

        # The actual cache dictionary, from which we store objects indexed by
        # their ObjectId
        self._cache = {}

    def __getitem__(self, key):
        """
        Return the object in cache stored at key :param:`key`

        Raise `KeyError`

        :param `key`: The key of the object to get
        """
        if not self.is_enabled:
            raise KeyError

        return self._cache[key]

    def __setitem__(self, key, value):
        """
        Sets an element in the cache at the id :param:`key`.

        :param key: Key of the object, must be an :class:`bson.objectid.ObjectId`

        :param value: Value to store
        """
        if not self.is_enabled:
            return value

        if not isinstance(key, ObjectId):
            raise TypeError('key must be of type ObjectId')

        self._cache[key] = value

    def __delitem__(self, key):
        """
        Deletes an element of the cache according to its
        :class:`bson.objectid.ObjectId` as :param:`key`.

        :param key: key of the element to delete
        """
        del self._cache[key]

    def __len__(self):
        """
        Returns the number of objects in cache.
        """
        if not self.is_enabled:
            return 0

        return len(self._cache)

    def __contains__(self, key):
        """
        Returns `True` if an item with the key :param:`item` is in the cache,
        `False` otherwise.

        :param key: Key to test
        """
        return self.is_enabled and key in self._cache

    def iteritems(self):
        """
        Return an iterator over the cache’s (key, value) pairs.
        """
        if not self.is_enabled:
            return {}.iteritems()

        return self._cache.iteritems()

    def __iter__(self):
        """
        Returns an iterator on the cache keys.
        """
        if not self.is_enabled:
            return {}.iterkeys()

        return self._cache.iterkeys()

class ObjectCacheCollection:
    """
    Holds a collection of :class:`ObjectCache` instances indexed by unique
    strings.
    """
    # Dictionary of ObjectCache for each collection we returned
    _object_cache_per_collection = {}

    def enable_caches(self):
        """
        Enable any cache in the collection.
        """
        for key in self._object_cache_per_collection:
            self._object_cache_per_collection[key].is_enabled = True

    def disable_caches(self):
        """
        Disable any cache in the collection.
        """
        for key in self._object_cache_per_collection:
            self._object_cache_per_collection[key].is_enabled = False

    def clear_caches(self):
        """
        Clear any cache in the collection.
        """
        for key in self._object_cache_per_collection:
            self._object_cache_per_collection[key].clear()

    def get_cache(self, name, create_if_needed = False):
        """
        Returns the :class:`ObjectCache` of the collection identified by its
        name.

        :param name: Name of the collection of which the cache object must be
        returned

        :param create_if_needed: Whether we want to create a new
        :class:`ObjectCache` if none exists for the collection

        Returns `None` if the cache is disabled, the :class:`ObjectCache: from
        the collection, a new one if :param:`create_if_needed` is `True` and
        the cache does not exist, or None.
        """
        try:
            return self._object_cache_per_collection[name]
        except KeyError:
            if create_if_needed:
                cache = ObjectCache()
                self.set_cache(name, cache)
                return cache
            else:
                return None

    def set_cache(self, name, cache):
        """
        Sets the :class:`ObjectCache` object for the collection named after
        :param:`name`.

        :param name: Name of the collection of which the cache object
        must be set.

        :param cache: :class:`ObjectCache` object
        """
        if not isinstance(cache, ObjectCache):
            raise TypeError("cache must be of type ObjectCache")

        self._object_cache_per_collection[name] = cache
