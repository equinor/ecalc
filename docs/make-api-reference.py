import shutil
from pathlib import Path

from pdoc import pdoc


def replace_in_file(file: Path, old_value: str, new_value: str):
    """
    Replaces a string in a file it the string is found in the file
    """
    with open(file, "r") as f:
        content = f.read()

    if old_value not in content:
        return

    content = content.replace(old_value, new_value)
    with open(file, "w") as f:
        f.write(content)


def replace_in_files(files: Path, old_value: str, new_value: str):
    """
    Replaces a string in a list if files if the string is found in the file
    """
    for file in files:
        replace_in_file(file, old_value, new_value)


if __name__ == "__main__":
    """
    Autogenerate python API documentation

    Output will be put in the docusaurus build directory
    """
    here = Path(__file__).parent
    out = here / "temp_api_docs"
    destination = here / "build" / "docs" / "about" / "references" / "api"
    if out.exists():
        shutil.rmtree(out)

    # Generate reference documentation using pdoc
    modules = ["libecalc", "!libecalc.core", "!libecalc.fixtures"]
    pdoc(*modules, output_directory=out)

    shutil.move(str(out / "libecalc.html"), str(destination))
    shutil.move(str(out / "libecalc"), str(destination))
    shutil.rmtree(out)

    # The API reference page in docusaurus contains a placeholder for the link to the generated docs page,
    # as the docusaurus build will fail on broken links when building before the API docs is generated.
    # This placeholder must be replaced in the docusaurus built code.

    placeholder = "[API_REFERENCE_LINK_PLACEHOLDER]"

    # Replace link placeholder in 'search-index.json'
    replace_in_file(here / "build" / "search-index.json", placeholder, "here")

    # Replace link placeholder in 'index.html'
    replace_in_file(
        destination / "index.html",
        placeholder,
        '<a target="_blank" href="/docs/about/references/api/libecalc.html">here</a>',
    )

    # Replace link placeholder in js assets
    files = (here / "build" / "assets" / "js").glob("*.js")
    replace_in_files(files, f'"{placeholder}"', '(0,i.kt)("a",{href:"./libecalc.html",target:"_blank"},"here")')
