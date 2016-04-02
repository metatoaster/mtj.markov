# -*- coding: utf-8 -*-
"""
Base modules.
"""


class State(object):
    """
    Base class for the representation of a state within a markov chain.

    Examples:
    
    - In a word generator, this simply is a letter.
    - In a sentence (or text) generator, this could simply be a word.
    - In simple weather model, this can be the amount of rainfall in an
      hour
    """


class StateTransition(object):
    """
    Base class for describing state transition using States.

    For referencing the leftmost or rightmost state, the identifier
    should be prefixed with 'l' or 'r', respectively.
    """

    def list_states(self):
        """
        Return a new list with all States that are involved with this
        state transition, i.e. for a first-order (order 1) markov model,
        a transition will have two states, result will be the two states
        (as a 2-tuple), and a second-order (order 2) markov model it
        will be three states, and so on.

        The actual value is implementation and usage specific, i.e. they
        could just be the primary keys, or the actual values, or both.
        """

        raise NotImplementedError

    def next(self, direction='lr'):
        """
        Return the next StateTransition.

        Direction: either 'lr' or 'rl', stands for left or right or right
        to left.
        """

        raise NotImplementedError


class StateGraph(object):
    """
    An abstract description that represents the engine that can generate
    a markov chain.
    """

    def __init__(self, engine):
        """
        engine - The engine that will run through this StateGraph.
        """

        self.engine = engine

    def merge(self, *a, **kw):
        """
        Take the provided raw arguments and merge them into this graph
        as StateTransition objets and associated State objects.
        """

        raise NotImplementedError

    def generate(self, count, state_transition=None, direction='lr'):
        """
        Yield up to count states or state transitions (whichever is
        convenient for representation), starting from state_transition.

        Default state_transition is implementation specific.
        """

        raise NotImplementedError

    def pick_state_transition(self, *a, **kw):
        """
        Return a state_transition based on arguments.  Return value must
        be a StateTransition type, that can serve as the starting
        value for the generate method.
        """

        raise NotImplementedError
