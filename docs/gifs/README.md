# How to generate eCalc CLI gifs for documentation

Install `vhs` as per their [documentation](https://github.com/charmbracelet/vhs?tab=readme-ov-file#installation), then restart your shell.

Create a venv and install `libecalc` in this directory.

```sh
python -m venv venv
source venv/bin/activate
pip install libecalc
```

The `.tape`-file is the script showing what will be run when creating the `.gif`.

To generate a new `.gif`, run `vhs` with the desired `.tape` file.:

```sh
vhs selftest.tape
```
