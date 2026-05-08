"""
Very simple way of visualizing the architecture/modules in libecalc.
Might be useful.
Currently set to top level modules only.
"""

from pathlib import Path

from matplotlib import pyplot as plt
from pytestarch import get_evaluable_architecture

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent.parent
    root_dir = root_dir / "src" / "libecalc"
    arch = get_evaluable_architecture(
        str(root_dir), str(root_dir), level_limit=1, exclusions=("*__pycache__*", "*__init__.py*")
    )
    arch.visualize()
    plt.show()
