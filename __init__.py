# python >= 3.6
""" This is the AstroPy module for writing astro libraries in Python.
The way this works, is you register your function with the correct
parameters, process some data in it and then exit the function to
continue running the astro script. On the asx script side, you need
a simple @mixin lib_function in order to execute the function with
the current data in the scope.
"""
import re

__author__  = 'bellrise'
__version__ = '0.1.2'


# Interface imports
from .objects import Scope, Mixin
from . import errors
from . import models


def render(func, lib: str, name: str):
    """ Returns a mixin object for the interpreter to execute when it
    is called in asx code with the @mixin instruction. """

    for i in [lib, name]:
        if not re.match('[A-z].+', i):
            raise RuntimeError('Invalid mixin name')

    return Mixin(func, lib, name)


def mixin(func):
    """ mixin wrapper, just a easier way to make this a bit safer """
    def wrapper(scope):
        func(scope)
        return scope.format()
    return wrapper