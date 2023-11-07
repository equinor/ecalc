def replace_placeholder_property_with_legacy_ref(schema: dict, property_key: str, property_ref: str) -> None:
    """
    Replace a property with a $ref to an existing json-schema file. This method exists so that we can gradually replace
    all json-schema files with pydantic classes that can generate the schema. Instead of converting all schemas at once,
    we can use this method to inject the old schemas for some properties in the class we are converting.

    This method will delete the type property, and inject the given $ref.

    :param schema: the generated pydantic schema
    :param property_key: the property key to replace with a $ref
    :param property_ref: the $ref path
    :return:
    """
    del schema["properties"][property_key]["type"]
    schema["properties"][property_key]["$ref"] = property_ref


def replace_temporal_placeholder_property_with_legacy_ref(schema: dict, property_key: str, property_ref: str) -> None:
    for value in schema["properties"][property_key]["anyOf"]:
        if "additionalProperties" in value:
            # Replace type in additional properties (temporal)
            # This will also replace for patternProperties since it is the same object used for both.
            additional_properties = value["additionalProperties"]
            del additional_properties["type"]
            additional_properties["$ref"] = property_ref
        else:
            # Replace type when not temporal
            del value["type"]
            value["$ref"] = property_ref
