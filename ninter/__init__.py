"""
Objects to use other interpreters like python.
Now, R and Deno is available.
"""
from . import interpreter
from . import base
from .base import Bridge, Let, Const
from .interpreter import R, Deno


def start_r():
    return Bridge(R())

def start_deno():
    return Bridge(Deno())
