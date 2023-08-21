from pathlib import Path

import typer
import typer.core
import typer_cli_stub as typer_cli

app = typer.Typer()

docusaurus_markdown_front_matter = """---
sidebar_label: "CLI"
---

"""


@app.command()
def generate(
    ctx: typer.Context,
    name: str = typer.Option("", help="The name of the CLI program to use in docs."),
    output: Path = typer.Option(
        None,
        help="An output file to write docs to, like README.md.",
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Generate Markdown docs for a Typer app."""
    # Ref: https://github.com/tiangolo/typer-cli/pull/67#issuecomment-1271983950
    from cli.main import app as main_app

    click_obj = typer.main.get_command(main_app)
    docs = typer_cli.get_docs_for_click(obj=click_obj, ctx=ctx, name=name)

    clean_docs = f"{docusaurus_markdown_front_matter}{docs.strip()}\n"
    if output:
        output.write_text(clean_docs)
        typer.echo(f"Docs saved to: {output}")
    else:
        typer.echo(clean_docs)


if __name__ == "__main__":
    app()
