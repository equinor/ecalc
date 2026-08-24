from datetime import datetime

from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.variables_graph import VariablesGraph
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable


def _var(expr_str: str) -> YamlSingleVariable:
    return YamlSingleVariable(value=Expression.setup_from_expression(expr_str))


class TestGetDirectReferences:
    def test_single_variable_with_time_series_ref(self):
        graph = VariablesGraph({"x": _var("SIM;col1 {+} 1")})
        assert graph.get_direct_references("x") == {"SIM;col1"}

    def test_single_variable_with_var_ref(self):
        graph = VariablesGraph(
            {
                "a": _var("SIM;col1"),
                "b": _var("$var.a {+} 1"),
            }
        )
        assert graph.get_direct_references("b") == {"$var.a"}

    def test_single_variable_multiple_refs(self):
        graph = VariablesGraph({"x": _var("SIM;col1 {+} SIM;col2")})
        assert graph.get_direct_references("x") == {"SIM;col1", "SIM;col2"}

    def test_unknown_variable_returns_empty(self):
        graph = VariablesGraph({"x": _var("SIM;col1")})
        assert graph.get_direct_references("nonexistent") == set()

    def test_constant_expression_no_refs(self):
        graph = VariablesGraph({"x": _var("42")})
        assert graph.get_direct_references("x") == set()

    def test_time_variable(self):
        """YamlTimeVariable: dict[datetime, YamlSingleVariable]."""
        time_var = {
            datetime(2020, 1, 1): _var("SIM;col1"),
            datetime(2021, 1, 1): _var("SIM;col2"),
        }
        graph = VariablesGraph({"x": time_var})
        assert graph.get_direct_references("x") == {"SIM;col1", "SIM;col2"}


class TestGetReferences:
    def test_direct_time_series_ref(self):
        graph = VariablesGraph({"x": _var("SIM;col1")})
        assert graph.get_references({"x"}) == {"SIM;col1"}

    def test_transitive_resolution(self):
        graph = VariablesGraph(
            {
                "a": _var("SIM;col1"),
                "b": _var("$var.a {+} 1"),
            }
        )
        refs = graph.get_references({"b"})
        assert "SIM;col1" in refs
        assert "$var.a" in refs

    def test_deep_transitive_chain(self):
        graph = VariablesGraph(
            {
                "a": _var("SIM;col1"),
                "b": _var("$var.a"),
                "c": _var("$var.b"),
            }
        )
        refs = graph.get_references({"c"})
        assert "SIM;col1" in refs

    def test_multiple_starting_variables(self):
        graph = VariablesGraph(
            {
                "a": _var("SIM;col1"),
                "b": _var("SIM;col2"),
            }
        )
        refs = graph.get_references({"a", "b"})
        assert refs == {"SIM;col1", "SIM;col2"}

    def test_cycle_does_not_loop(self):
        """Variables referencing each other should not cause infinite loop."""
        graph = VariablesGraph(
            {
                "a": _var("$var.b"),
                "b": _var("$var.a"),
            }
        )
        refs = graph.get_references({"a"})
        assert "$var.b" in refs
        assert "$var.a" in refs

    def test_empty_variable_names(self):
        graph = VariablesGraph({"x": _var("SIM;col1")})
        assert graph.get_references(set()) == set()

    def test_unknown_variable_names(self):
        graph = VariablesGraph({"x": _var("SIM;col1")})
        assert graph.get_references({"nonexistent"}) == set()

    def test_diamond_dependency(self):
        graph = VariablesGraph(
            {
                "a": _var("SIM;col1"),
                "b": _var("$var.a"),
                "c": _var("$var.a"),
                "d": _var("$var.b {+} $var.c"),
            }
        )
        refs = graph.get_references({"d"})
        assert "SIM;col1" in refs
