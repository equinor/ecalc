def to_camel_case(string: str) -> str:
    string_split = string.replace("__", "_").split("_")
    return string_split[0] + "".join(word[0].upper() + word[1:] for word in string_split[1:])
