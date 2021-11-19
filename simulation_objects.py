from typing import Any


class _IntRepresentation:
    def __eq__(self, o: object) -> bool:
        if hasattr(o, 'int_representation'):
            return self.int_representation == o.int_representation
        else:
            try:
                return _IntRepresentation(o) == self
            except:
                return False

    def __repr__(self) -> str:
        return str(self.int_representation)

    def __init__(self, int_or_array):
        if hasattr(int_or_array, 'int_representation'):
            self.int_representation = int_or_array.int_representation
        elif isinstance(int_or_array, int):
            self.int_representation = int_or_array
        elif isinstance(int_or_array, list):
            self.int_representation = int(''.join(map(lambda x: '1' if x else '0', int_or_array)), 2)
        else:
            raise TypeError('int_or_array must be int or array')

    def lookup(self, state) -> bool:
        return bool((self.int_representation >> state) & 1)


class State(_IntRepresentation):
    def __init__(self, int_or_array, variables=-1):
        super().__init__(int_or_array)
        if hasattr(int_or_array, 'variables'):
            self.variables = int_or_array.variables
        else:
            self.variables = variables
        if variables == -1 and isinstance(int_or_array, list):
            self.variables = len(int_or_array)

    def __getitem__(self, item):
        return self.lookup(item)

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if value:
                self.int_representation = self.int_representation | (1 << key)
            else:
                self.int_representation = self.int_representation & ~(1 << key)
        else:
            raise TypeError('key must be int')

    def overwrite(self, with_state):
        new_state = self.int_representation
        if with_state.variables >=0:
            if hasattr(with_state, "offset"):
                mask = ((1 << with_state.variables) - 1) << with_state.offset
                new_state |= (with_state.int_representation << with_state.offset) & mask
                new_state &= (with_state.int_representation << with_state.offset) | ~mask
            else:
                mask = (1 << with_state.variables) - 1
                new_state |= with_state.int_representation & mask
                new_state &= with_state.int_representation | ~mask
        else:
            raise TypeError('with_state must have variables count')

        return new_state


class SubState(State):
    def __init__(self, int_or_array, variables=-1, offset=0):
        super().__init__(int_or_array, variables)
        self.offset = offset


class RuleDependencies(_IntRepresentation):
    def map(self, state):
        temp = self.int_representation
        mask = 1
        bit = 0
        selected = 0
        while temp:
            if temp & 1:
                selected = selected | ((1 if (state.int_representation & mask) else 0) << bit)
                bit += 1
            temp >>= 1
            mask <<= 1
        return State(selected)


class RuleFunctionElement(_IntRepresentation):
    def __init__(self, int_or_array):
        super().__init__(int_or_array)

    def evaluate(self, state: State):
        return self.lookup(state.int_representation)


class RuleFunction:
    def __init__(self, elements: list, dependencies: RuleDependencies):
        self.elements = [RuleFunctionElement(e) for e in elements]
        self.dependencies = RuleDependencies(dependencies)

    def evaluate(self, state):
        subspace = self.dependencies.map(state)
        return State([e.evaluate(subspace) for e in self.elements], len(self.elements))


class Node:
    def __init__(self, id, rule_function: RuleFunction, initial_state: State, global_state_offset: int):
        self.id = id
        self.rule_function = rule_function
        self.local_state = initial_state
        self.global_state_offset = global_state_offset
        self.number_of_variables = len(rule_function.elements)
        self.state_history = [(initial_state.int_representation, 0)]
        self.reached_states = set([initial_state.int_representation])

    def evaluate_rule(self) -> SubState:
        return SubState(self.rule_function.evaluate(self.local_state), offset=self.global_state_offset)

    def global_sub_state(self) -> SubState:
        return SubState((self.local_state.int_representation >> self.global_state_offset) &
                        (pow(2, self.number_of_variables) - 1),
                        variables=self.number_of_variables, offset=self.global_state_offset)
