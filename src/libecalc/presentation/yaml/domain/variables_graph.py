from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlSingleVariable,
    YamlVariables,
)


class VariablesGraph:
    """Graph of $var.* dependencies with methods to resolve transitive time series references."""

    def __init__(self, variables: YamlVariables):
        self._references: dict[str, set[str]] = {}
        for name, variable in variables.items():
            if isinstance(variable, YamlSingleVariable):
                refs = set(variable.value.variables)
            else:
                refs = {v for expr in variable.values() for v in expr.value.variables}
            self._references[name] = refs

    def get_direct_references(self, variable_name: str) -> set[str]:
        """All direct references (both $var.* and time series) for a variable."""
        return self._references.get(variable_name, set())

    def get_references(self, variable_names: set[str]) -> set[str]:
        """Transitively resolve a set of $var.* names to all time series references they depend on.

        Args:
            variable_names: Variable names without the ``$var.`` prefix.

        Returns:
            Set of time series references (e.g. ``{"SIM1;OIL_PROD"}``).
        """
        visited: set[str] = set()
        refs: set[str] = set()
        stack = list(variable_names)

        while stack:
            name = stack.pop()
            if name in visited:
                continue
            visited.add(name)

            for ref in self.get_direct_references(name):
                refs.add(ref)
                if ref.startswith("$var."):
                    stack.append(ref.removeprefix("$var."))

        return refs
