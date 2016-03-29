# -*- coding: utf-8 -*-

def pair(items):
    """
    Generator that generates pairs of preceding and subsequent items for
    the given iterable.
    """

    if len(items) < 2:
        return []
    result = []
    previous = items[0]
    for item in items[1:]:
        yield previous, item
        previous = item
