from ecalc_cli.commands import show


def generate_json_schema_reference() -> None:
    """Generate JSON schema and write to stdout"""
    show.show_schema(output_file=None)


if __name__ == "__main__":
    generate_json_schema_reference()
