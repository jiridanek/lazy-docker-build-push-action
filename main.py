#!/usr/bin/env python3

from __future__ import annotations

import os
import uuid
import hashlib
import argparse
import itertools
import subprocess
import collections
from pathlib import Path

GITHUB_ACTIONS = bool(os.environ.get('GITHUB_ACTIONS'))

# Keep order the same as the README's list of what affects the hash.
DOCKER_INPUTS = (
    'annotations',
    'build-args',
    'build-contexts',
    'target',
    'ulimit',
    'labels',
)


class MissingInput(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Missing value for input {name!r}")
        self.name = name


def _get_input(name: str) -> str:
    # https://github.com/actions/toolkit/blob/ae38557bb0dba824cdda26ce787bd6b66cf07a83/packages/core/src/core.ts#L128
    env_name = name.replace(' ', '_').upper()
    return os.environ.get(f'INPUT_{env_name}', '')


def get_input(name: str, required: bool = False) -> str:
    value = _get_input(name)
    if required and not value:
        raise MissingInput(name)
    return value.strip()


def _get_list(value: str) -> list[str]:
    # Note: this is not fully generalised -- `docker/build-push-action` (via
    # `@docker/actions-toolkit`) has somewhat more complex parsing for some
    # cases. For the single case we currently use this (the `tags` input), this
    # implementation is believed to be close enough.
    return list(itertools.chain.from_iterable(
        (x.strip() for x in x.split(','))
        for x in value.splitlines()
    ))


def _get_input_list(name: str, required: bool = False) -> list[str]:
    # Note: not fully general -- see warning in `_get_list`.
    return _get_list(get_input(name, required))


def set_output(name: str, value: str | bool | list[str]) -> None:
    if isinstance(value, list):
        value = '\n'.join(value)

    elif isinstance(value, bool):
        value = 'true' if value else 'false'

    print(f"Output: {name}={value!r}")

    if GITHUB_ACTIONS:
        delimiter = f'gh-delim-{uuid.uuid4()}'
        with open(os.environ['GITHUB_OUTPUT'], mode='a') as f:
            # https://github.com/actions/toolkit/blob/ae38557bb0dba824cdda26ce787bd6b66cf07a83/packages/core/src/file-command.ts#L46
            print(f'{name}<<{delimiter}\n{value}\n{delimiter}', file=f)


def get_dockerfile() -> Path:
    if dockerfile := get_input('file'):
        return Path(dockerfile)
    return Path(get_input('context') or '.') / 'Dockerfile'


def get_tags() -> list[str]:
    return _get_input_list('tags', required=True)


def image_exists(name_tag: str) -> bool:
    # Check locally first, mostly for developer convenience -- we don't really
    # expect the image to available locally when used in an Action.
    try:
        subprocess.check_call(
            ['docker', 'image', 'inspect', name_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.check_call(
            ['docker', 'manifest', 'inspect', name_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def compute_hash(filenames: list[Path]) -> str:
    hasher = hashlib.sha256()

    for name in sorted(DOCKER_INPUTS):
        value = get_input(name, required=False)
        hasher.update(f'docker:{name}={value!r}\n'.encode())

    for filename in sorted((*filenames, get_dockerfile())):
        hasher.update(f'file:{filename}\n----\n'.encode())
        with filename.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        hasher.update(b'\n----\n')

    return f'content-hash-{hasher.hexdigest()}'


def get_image_names(content_hash_tag: str) -> tuple[list[str], list[str]]:
    input_tags = get_tags()

    images: dict[str, set[str]]
    images = collections.defaultdict(lambda: {content_hash_tag})
    for input_tag in input_tags:
        name, _, tag = input_tag.partition(':')
        image_tags = images[name]
        if tag:
            image_tags.add(tag)

    all_tags = [
        f'{name}:{tag}'
        for name, tags in images.items()
        for tag in tags
    ]
    content_hash_tags = [
        f'{name}:{content_hash_tag}'
        for name in images.keys()
    ]
    return all_tags, content_hash_tags


def main(extra_files: list[Path]) -> None:
    content_hash_tag = compute_hash(extra_files)
    all_tags, content_hashed_tags = get_image_names(content_hash_tag)

    exists = {x: image_exists(x) for x in content_hashed_tags}

    set_output('tags', all_tags)

    tag_existed = any(exists.values())
    set_output('tag-existed', tag_existed)
    set_output('build-required', not tag_existed)

    name, _, tag = (name_tag := content_hashed_tags[0]).partition(':')
    assert content_hash_tag == tag
    set_output('image-name', name)
    set_output('image-tag', tag)
    set_output('image-name-tag', name_tag)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lazy Docker build manager")
    parser.add_argument(
        '--files',
        type=Path,
        nargs=argparse.ONE_OR_MORE,
        default=[],
        help="Extra files to include in the content hash.",
    )
    return parser.parse_args()


def cli(args: argparse.Namespace) -> None:
    try:
        main(args.files)
    except MissingInput as e:
        exit(str(e))


if __name__ == '__main__':
    cli(parse_args())
