#!/usr/bin/env python3

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

from main import get_input, set_output

GITHUB_ACTIONS = bool(os.environ.get('GITHUB_ACTIONS'))


def setup_sandbox(paths: list[pathlib.Path], tmpdir: pathlib.Path):
    for path in paths:
        if path.is_dir():
            shutil.copytree(path, tmpdir / path, symlinks=False, dirs_exist_ok=True)
        else:
            (tmpdir / path.parent).mkdir(parents=True, exist_ok=True)
            shutil.copy(path, tmpdir / path.parent)


def main() -> int:
    context = pathlib.Path(get_input("context") or ".")
    extra_inputs = [pathlib.Path(path) for path in get_input("extra-inputs").split(' ')]  # todo: why space and not '\n'
    build_contexts = {}
    for build_context in get_input("build-contexts").split('\n'):
        name, *path = build_context.split('=', maxsplit=1)
        if not name or len(path) != 1:
            continue
        build_contexts[name] = pathlib.Path(path[0])

    # create sandbox directory
    tmpdir = pathlib.Path(tempfile.mkdtemp())

    # add Dockerfile to sandbox if location is not specified elsewhere
    if not get_input("file"):
        extra_inputs.append(context / "Dockerfile")
    # add .dockerignore to the sandbox, even if unspecified
    if (dockerignore := (context / ".dockerignore")).exists():
        extra_inputs.append(dockerignore)

    setup_sandbox(extra_inputs, tmpdir)

    set_output("tmpdir", str(tmpdir.absolute()))
    set_output("context", str(tmpdir / context))
    set_output("build-contexts", '\n'.join(f"{name}={str(tmpdir / path)}" for name, path in build_contexts.values()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
