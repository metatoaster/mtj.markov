# -*- coding: utf-8 -*-
"""
Base modules.
"""


class Node(object):
    """
    A node within the graph.
    """


class Graph(object):
    """
    The graph.
    """


class Datum(Node):
    """
    Base class for the representation of a single unit of data to be
    added to the markov engine.

    Examples:

    - A given source word for a word generator.
    - The sentence (or some text) to be added to a markov text graph.
    - In simple weather model, a chain of possible weather events over a
      series of fixed time periods amounting to a typical cycle length.

    Althugh typically, these raw datum are never stored, but rather they
    are reduced to some unique identifier where it can be used as a
    starting point to regnerate the original from the other parts the
    added data.
    """


class Normalized(Node):
    """
    Normalized data nodes.  It should have an id, and the data should be
    unique over the entire table/graph.
    """


class State(Normalized):
    """
    Base class for the representation of a state within a markov chain.

    Examples:
    
    - In a word generator, this simply is a letter.
    - In a sentence (or text) generator, this could simply be a word.
    - In simple weather model, this can be the amount of rainfall and/or
      the amount of sunshine received over a fixed time period.
    """


class Index(Node):
    """
    Base class for representing an index

    This is for the storage of normalized form of similar data and/or to
    facilitate lookup of states and/or state transitions, depending on
    the specific implementation of the engine.
    """


class StateTransition(Node):
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


class StateGraph(Graph):
    """
    A description containing all state transitions and states for the
    generation of a markov chain.
    """

    def __init__(self, *a, **kw):
        """
        Initialize the graph - it can contain parameters such as
        restrictions to what constitutes as valid input for the learning
        method, etc.
        """

        raise NotImplementedError

    def initialize(self, *a, **kw):
        """
        The actual initialization method.  Attributes relating to
        location of the persistent store for the rules and other related
        attributes should be initialized here.
        """

        raise NotImplementedError

    def learn(self, *a, **kw):
        """
        Turn the arguments into State and StateTransition objects and
        merge them into this StateGraph.
        """

        raise NotImplementedError

    def merge(self, state_transitions):
        """
        Merge the list of StateTransition objects and its associated
        State objects (defined within its relationships) into this
        graph.
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
