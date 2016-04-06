# -*- coding: utf-8 -*-


def nchain(count, items):
    """
    Return a generator that generates pairs of preceding and subsequent
    items for the given iterable.
    """

    if len(items) < count:
        return []
    idx = count - 1
    return (tuple(items[c:c + count]) for c, item in enumerate(items[:-idx]))


def pair(items):
    return nchain(2, items)


def unique_merge(session, model, **kw):
    result = session.query(model).filter_by(**kw).first()
    if not result:
        result = session.merge(model(**kw))
    return result
