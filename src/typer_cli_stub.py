from typing import cast

import typer
from click import Command, Group

"""
The code gist in this file is extracted from https://github.com/tiangolo/typer-cli/tree/master

Due to lack of compatibility of newer Typer releases we saw the need to extract the small portion
of the code that we use to generate API documentation for the CLI, instead of being forced to
use old versions of Typer.

The code is provided under the following copyright statement and license:

The MIT License (MIT)

Copyright (c) 2020 Sebastián Ramírez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


def get_docs_for_click(
    *,
    obj: Command,
    ctx: typer.Context,
    indent: int = 0,
    name: str = "",
    call_prefix: str = "",
) -> str:
    docs = "#" * (1 + indent)
    command_name = name or obj.name
    if call_prefix:
        command_name = f"{call_prefix} {command_name}"
    title = f"`{command_name}`" if command_name else "CLI"
    docs += f" {title}\n\n"
    if obj.help:
        docs += f"{obj.help}\n\n"
    usage_pieces = obj.collect_usage_pieces(ctx)
    if usage_pieces:
        docs += "**Usage**:\n\n"
        docs += "```console\n"
        docs += "$ "
        if command_name:
            docs += f"{command_name} "
        docs += f"{' '.join(usage_pieces)}\n"
        docs += "```\n\n"
    args = []
    opts = []
    for param in obj.get_params(ctx):
        rv = param.get_help_record(ctx)
        if rv is not None:
            if param.param_type_name == "argument":
                args.append(rv)
            elif param.param_type_name == "option":
                opts.append(rv)
    if args:
        docs += "**Arguments**:\n\n"
        for arg_name, arg_help in args:
            docs += f"* `{arg_name}`"
            if arg_help:
                docs += f": {arg_help}"
            docs += "\n"
        docs += "\n"
    if opts:
        docs += "**Options**:\n\n"
        for opt_name, opt_help in opts:
            docs += f"* `{opt_name}`"
            if opt_help:
                docs += f": {opt_help}"
            docs += "\n"
        docs += "\n"
    if obj.epilog:
        docs += f"{obj.epilog}\n\n"
    if isinstance(obj, Group):
        group: Group = cast(Group, obj)
        commands = group.list_commands(ctx)
        if commands:
            docs += "**Commands**:\n\n"
            for command in commands:
                command_obj = group.get_command(ctx, command)
                assert command_obj
                docs += f"* `{command_obj.name}`"
                command_help = command_obj.get_short_help_str()
                if command_help:
                    docs += f": {command_help}"
                docs += "\n"
            docs += "\n"
        for command in commands:
            command_obj = group.get_command(ctx, command)
            assert command_obj
            use_prefix = ""
            if command_name:
                use_prefix += f"{command_name}"
            docs += get_docs_for_click(obj=command_obj, ctx=ctx, indent=indent + 1, call_prefix=use_prefix)
    return docs
