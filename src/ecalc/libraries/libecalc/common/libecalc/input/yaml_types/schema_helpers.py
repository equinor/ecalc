def replace_placeholder_property_with_legacy_ref(schema: dict, property_key: str, property_ref: str) -> None:
    """
    Replace a property with a $ref to an existing json-schema file. This method exists so that we can gradually replace
    all json-schema files with pydantic classes that can generate the schema. Instead of converting all schemas at once,
    we can use this method to inject the old schemas for some of the properties in the class we are converting.

    This method will delete the type property, and inject the given $ref.

    :param schema: the generated pydantic schema
    :param property_key: the property key to replace with a $ref
    :param property_ref: the $ref path
    :return:
    """
    del schema["properties"][property_key]["type"]
    schema["properties"][property_key]["$ref"] = property_ref
