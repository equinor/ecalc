from pathlib import Path

from pytestarch import get_evaluable_architecture

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent.parent.parent / "libecalc" / "src"
    src_dir = root_dir.parent / "src"
    arch = get_evaluable_architecture(str(root_dir), str(src_dir))
    arch.visualize()
