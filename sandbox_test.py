import glob
import logging
import pathlib
import tempfile

import pytest
import pyfakefs.fake_filesystem

from sandbox import setup_sandbox

# make it clear pytest is required to run the tests
_ = pytest


class TestSandbox:
    def test_filesystem_file(self, fs: pyfakefs.fake_filesystem.FakeFilesystem):
        pathlib.Path("a").write_text("a")

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_sandbox([pathlib.Path("a")], pathlib.Path(tmpdir))
            assert (pathlib.Path(tmpdir) / "a").is_file()

    def test_filesystem_dir_with_file(self, fs: pyfakefs.fake_filesystem.FakeFilesystem):
        pathlib.Path("a/").mkdir()
        pathlib.Path("a/b").write_text("b")

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_sandbox([pathlib.Path("a")], pathlib.Path(tmpdir))
            assert (pathlib.Path(tmpdir) / "a").is_dir()
            assert (pathlib.Path(tmpdir) / "a" / "b").is_file()

    def test_filesystem_dir_with_dir_with_file(self, fs: pyfakefs.fake_filesystem.FakeFilesystem):
        pathlib.Path("a/b").mkdir(parents=True)
        pathlib.Path("a/b/c").write_text("c")

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_sandbox([pathlib.Path("a")], pathlib.Path(tmpdir))
            assert (pathlib.Path(tmpdir) / "a").is_dir()
            assert (pathlib.Path(tmpdir) / "a" / "b").is_dir()
            assert (pathlib.Path(tmpdir) / "a" / "b" / "c").is_file()

    def test_filesystem_file_in_dir_in_dir(self, fs: pyfakefs.fake_filesystem.FakeFilesystem):
        pathlib.Path("a/b").mkdir(parents=True)
        pathlib.Path("a/b/c").write_text("c")

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_sandbox([pathlib.Path("a/b/c")], pathlib.Path(tmpdir))
            for g in glob.glob("**/*", recursive=True):
                logging.debug("%s", g)
            assert (pathlib.Path(tmpdir) / "a").is_dir()
            assert (pathlib.Path(tmpdir) / "a" / "b").is_dir()
            assert (pathlib.Path(tmpdir) / "a" / "b" / "c").is_file()
