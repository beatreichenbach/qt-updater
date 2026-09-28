"""
Run an update of the host application.

This module runs as a standalone script, so it is imported by full path.
Relative imports would fail here, so it imports the public API by absolute name.
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from qt_updater import (
    Install,
    InstallError,
    Kind,
    Release,
    UpdaterError,
    detect_install,
    format_command,
    update_commands,
)

logger = logging.getLogger(__name__)

TEMP_PREFIX = 'qt_update_'


def main(arguments: list[str]) -> int:
    """
    Run an update from the given arguments and return a process exit code.

    The arguments are ``package``, ``tag`` and an optional ``source_url``.
    """

    if len(arguments) < 2:
        logger.error('usage: updater.py PACKAGE TAG [SOURCE_URL]')
        return 2

    package, tag, *rest = arguments
    release = Release(tag=tag, source_url=rest[0] if rest else '')

    try:
        return run(detect_install(package), package, release)
    except Exception as error:
        logger.error(f'{error}')
        return 2


def run(install: Install, package: str, release: Release) -> int:
    """Apply an update for an install and return a process exit code."""

    logger.info(f'Updating {package} to {release.version}')

    if install.kind == Kind.SOURCE and not install.editable:
        apply_source_archive(install, package, release.source_url)

    for command in update_commands(install, package, release):
        code = execute(command)
        if code != 0:
            return code

    logger.info('Update complete.')
    return 0


def apply_source_archive(
    install: Install,
    package: str,
    source_url: str,
) -> None:
    """
    Replace a downloaded source tree with the release archive.

    :raises UpdaterError: if the install or archive is invalid.
    """

    if install.root is None:
        raise InstallError('the source install has no directory')
    if not source_url:
        raise UpdaterError('the release has no source archive')

    archive = download(source_url)
    staging = create_staging(install.root)
    try:
        source = extract(archive, staging)
        check_source(source, package)
        swap_package_dir(install.root, source, package)
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)


def create_staging(root: Path) -> Path:
    """Create and return a staging directory next to the install root."""

    try:
        return Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=str(root.parent)))
    except OSError:
        return Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))


def check_source(source: Path, package: str) -> None:
    """
    Raise if a source tree is not a valid checkout of the package.

    :raises UpdaterError: if the tree is invalid.
    """

    if not (source / package).is_dir() or not (source / 'pyproject.toml').exists():
        raise UpdaterError('the archive does not contain a source tree')


def swap_package_dir(root: Path, source: Path, package: str) -> None:
    """Swap the package directory for the new one, restoring it on failure."""

    backup = root / f'.{package}-backup'
    shutil.rmtree(backup, ignore_errors=True)
    shutil.move(str(root / package), str(backup))

    try:
        shutil.move(str(source / package), str(root / package))

        # The package directory was moved out of the source above, so this
        # copies only the remaining top level entries.
        for entry in source.iterdir():
            target = root / entry.name
            if entry.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(entry, target)
            else:
                shutil.copy2(entry, target)
    except Exception:
        shutil.rmtree(root / package, ignore_errors=True)
        shutil.move(str(backup), str(root / package))
        raise

    shutil.rmtree(backup, ignore_errors=True)


def download(url: str) -> Path:
    """Download a file and return its temporary path."""

    logger.info(f'Downloading: {url}')
    descriptor, name = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix='.zip')
    with (
        os.fdopen(descriptor, 'wb') as target,
        urllib.request.urlopen(url, timeout=60) as response,
    ):
        shutil.copyfileobj(response, target)
    return Path(name)


def extract(archive: Path, destination: Path) -> Path:
    """
    Extract an archive and return its source directory.

    :raises UpdaterError: if the archive is empty.
    """

    with zipfile.ZipFile(archive) as file:
        file.extractall(destination)

    entries = list(destination.iterdir())
    if not entries:
        raise UpdaterError('the archive is empty')
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return destination


def execute(command: list[str]) -> int:
    """Run a command, streaming its output, and return its exit code."""

    logger.info(format_command(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        logger.error(f'command failed ({result.returncode})')
    return result.returncode


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, force=True)
    raise SystemExit(main(sys.argv[1:]))
