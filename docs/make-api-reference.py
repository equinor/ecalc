import shutil
from pathlib import Path

from pdoc import pdoc


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
