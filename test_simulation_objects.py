from simulation_objects import RuleDependencies, RuleFunction, State, SubState


def test_state_selection_with_RuleDependencies():
    assert RuleDependencies([1,1,0,0]).map(State([0,1,1,0])) == State([0,1])
    assert RuleDependencies([1,1,0,0]).map(State([1,1,0,0])) == State([1,1])

def test_rule_evaluation_with_RuleFunction():
    assert RuleFunction([[1,1,0,0],[0,0,1,1]],[1,1,0,0]).evaluate(State([0,1,1,0])) == State([0,1])
    assert RuleFunction([[1,1,1,1],[1,1,1,1]],[1,1,0,0]).evaluate(State([0,1,1,0])) == State([1,1])

def test_state_overwriting():
    assert State([0,1,1,0]).overwrite(State([1,1,0,0]))==State([1,1,0,0])
    assert State([0,1,1,0]).overwrite(State([1,1]))==State([0,1,1,1])
    assert State([0,1,1,0]).overwrite(SubState([1,1],2))==State([1,1,1,0])