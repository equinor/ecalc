from libecalc.common.fluid import ComponentMolecularWeight, FluidComposition


def test_all_fluid_components_have_molecular_weights():
    """Test that all components in FluidComposition have corresponding molecular weights in ComponentMolecularWeight."""
    # Get all field names from FluidComposition
    fluid_components = FluidComposition.model_fields.keys()

    # Get all constants from ComponentMolecularWeight
    molecular_weight_components = {name for name in dir(ComponentMolecularWeight) if not name.startswith("_")}

    # For each component in FluidComposition, check if it has a corresponding molecular weight
    missing_components = []
    for component in fluid_components:
        component_upper = component.upper()
        if component_upper not in molecular_weight_components:
            missing_components.append(component)

    assert not missing_components, (
        f"The following components in FluidComposition are missing molecular weights in ComponentMolecularWeight: "
        f"{', '.join(missing_components)}"
    )
