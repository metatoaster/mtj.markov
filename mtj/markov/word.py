# -*- coding: utf-8 -*-
import re

# has at least a word char
has_word_char = re.compile('\w')
# match non-wordchars, lazy match wordchars, remainder non-wordchars.
punctuation_strip = re.compile('^\\W*(.+?)\\W*$')


def normalize(word):
    """
    Right now only do the most basic things

    - Strip off punctuation marks if this is an actual word
    - Normalize it to lowercase if istitle.

    Could make this as part of a plugin system, so that other, more
    advanced normalization methods can be done on a configuration basis.
    """

    result = word
    if has_word_char.search(word):
        # strip off leading and trailing punctuation marks
        result = punctuation_strip.sub('\\1', word)

    if result.istitle():
        result = result.lower()

    return result
