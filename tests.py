#!/usr/bin/env python3

import os
import tempfile
import unittest
from typing import Any
from pathlib import Path
from unittest import mock

import main


class Tests(unittest.TestCase):
    maxDiff = None

    _HASH = 'content-hash-facabdb2b0642ff20db8f3150326b37dfcc76755752109c2d917d7b9702268be'

    def setUp(self) -> None:
        super().setUp()

        directory = tempfile.TemporaryDirectory()
        os.chdir(directory.name)
        self.addCleanup(directory.cleanup)

        # Inputs

        self.dockerfile = open('Dockerfile', mode='w+t')
        self.addCleanup(self.dockerfile.close)

        self.inputs: dict[str, str] = {
            'tags': 'user/app',
        }

        def get_input(name: str) -> str:
            return self.inputs.get(name, '')

        patch = mock.patch(
            'main._get_input',
            autospec=True,
            side_effect=get_input,
        )
        patch.start()
        self.addCleanup(patch.stop)

        # Commands

        self.image_exists = False
        patch = mock.patch(
            'main.image_exists',
            autospec=True,
            side_effect=lambda *a, **k: self.image_exists,
        )
        patch.start()
        self.addCleanup(patch.stop)

        # Outputs

        self.outputs: dict[str, Any] = {}  # type: ignore[misc]  # explicit Any

        def set_output(name: str, value: str) -> None:
            self.outputs[name] = value

        patch = mock.patch(
            'main.set_output',
            autospec=True,
            side_effect=set_output,
        )
        patch.start()
        self.addCleanup(patch.stop)

    def test_no_tags(self) -> None:
        self.inputs.pop('tags')

        with self.assertRaises(main.MissingInput) as cm:
            main.main([])

        self.assertEqual('tags', cm.exception.name)

    def test_core(self) -> None:
        main.main([])

        self.assertEqual(
            {
                'build-required': True,
                'image-name': 'user/app',
                'image-name-tag': f'user/app:{self._HASH}',
                'image-tag': self._HASH,
                'tag-existed': False,
                'tags': [f'user/app:{self._HASH}'],
            },
            self.outputs,
        )

    def test_image_name_only(self) -> None:
        self.inputs['tags'] = 'user/app'

        main.main([])

        self.assertCountEqual(
            [f'user/app:{self._HASH}'],
            self.outputs['tags'],
        )

    def test_image_tag(self) -> None:
        self.inputs['tags'] = 'user/app:latest'

        main.main([])

        self.assertCountEqual(
            ['user/app:latest', f'user/app:{self._HASH}'],
            self.outputs['tags'],
        )
        self.assertEqual(
            f'user/app:{self._HASH}',
            self.outputs['image-name-tag'],
        )

    def test_several_image_tags(self) -> None:
        self.inputs['tags'] = 'user/app:latest, user/app:commit-abc\nuser/app:v1.2.3'

        main.main([])

        self.assertCountEqual(
            [
                'user/app:latest',
                'user/app:commit-abc',
                'user/app:v1.2.3',
                f'user/app:{self._HASH}',
            ],
            self.outputs['tags'],
        )
        self.assertEqual(
            f'user/app:{self._HASH}',
            self.outputs['image-name-tag'],
        )

    def test_several_image_names(self) -> None:
        self.inputs['tags'] = 'user/app:latest, ghr.io/user/app'

        main.main([])

        self.assertCountEqual(
            [
                'user/app:latest',
                f'user/app:{self._HASH}',
                f'ghr.io/user/app:{self._HASH}',
            ],
            self.outputs['tags'],
        )
        self.assertEqual(
            f'user/app:{self._HASH}',
            self.outputs['image-name-tag'],
        )

    def test_extra_files(self) -> None:
        other = Path('other.txt')
        with other.open(mode='w') as f:
            print("Bees", file=f)

        main.main([other])

        tag = 'content-hash-fc3cd4f2034293d3ca445cddb9d20dbfd2082087978050417c1dc7a5be0a9b3a'
        name_tag = f'user/app:{tag}'
        self.assertEqual(
            {
                'build-required': True,
                'image-name': 'user/app',
                'image-name-tag': name_tag,
                'image-tag': tag,
                'tag-existed': False,
                'tags': [name_tag],
            },
            self.outputs,
        )

    def test_explicit_file(self) -> None:
        with open('other.dockerfile', mode='w') as f:
            print("Moar", file=f)

        self.inputs['file'] = 'other.dockerfile'

        main.main([])

        tag = 'content-hash-d3a0a8c55dea39d9066a9c02748fcbbbf72db2284610fbb181156250438c9b86'
        name_tag = f'user/app:{tag}'
        self.assertEqual(
            {
                'build-required': True,
                'image-name': 'user/app',
                'image-name-tag': name_tag,
                'image-tag': tag,
                'tag-existed': False,
                'tags': [name_tag],
            },
            self.outputs,
        )


if __name__ == '__main__':
    unittest.main()
