# -*- coding: utf-8 -*-
"""
  This file is part of lisogo
  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

class Error(Exception):
    """
    Generic error raised when an error is raised in the package
    :pack:`lisogo.model`
    """
    pass

class PersistError(Error):
    """
    Generic exception raised when trying to persist an object to the database.
    """
    pass

class RetrieveError(Error):
    """
    Generic exception raised when trying to retrieve an object from the
    database.
    """
    pass

class NotFoundError(RetrieveError):
    """
    Error raised when no matching result is found while trying to retrieve one
    or more documents from a collection.
    """
    pass
