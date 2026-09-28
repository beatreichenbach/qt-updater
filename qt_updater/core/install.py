import dataclasses
import enum
import json
import shlex
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from .exceptions import InstallError
from .release import Release


class Manager(enum.StrEnum):
    UV = 'uv'
    PIP = 'pip'
    UV_TOOL = 'uv-tool'
    PIPX = 'pipx'


class Kind(enum.StrEnum):
    GIT = 'git'
    SOURCE = 'source'
    VCS = 'vcs'
    REGISTRY = 'registry'


@dataclasses.dataclass(frozen=True)
class Install:
    kind: Kind
    root: Path | None
    manager: Manager
    url: str | None = None
    editable: bool = False


def detect_install(package: str) -> Install:
    """
    Return how a package was installed.

    :raises InstallError: if the package is not installed.
    """

    try:
        dist = metadata.distribution(package)
    except metadata.PackageNotFoundError as error:
        raise InstallError(f'package is not installed: {package}') from error

    manager = _manager(dist)
    if manager in (Manager.UV_TOOL, Manager.PIPX):
        return Install(kind=Kind.REGISTRY, root=None, manager=manager)

    install = _install_from_direct_url(dist, manager)
    if install is not None:
        return install
    return Install(kind=Kind.REGISTRY, root=None, manager=manager)


def update_commands(
    install: Install, package: str, release: Release
) -> list[list[str]]:
    """Return the ordered commands that update an install."""

    return [*git_commands(install, release), manager_command(install, package, release)]


def git_commands(install: Install, release: Release) -> list[list[str]]:
    """Return the fetch and checkout commands for a git install."""

    if install.kind is not Kind.GIT or install.root is None:
        return []
    if not release.tag:
        return []

    return [
        ['git', '-C', str(install.root), 'fetch', '--tags', '--force'],
        ['git', '-C', str(install.root), 'checkout', f'tags/{release.tag}'],
    ]


def manager_command(install: Install, package: str, release: Release) -> list[str]:
    """Return the command that installs the target version."""

    if install.manager == Manager.UV_TOOL:
        return [Manager.UV, 'tool', 'upgrade', package]
    if install.manager == Manager.PIPX:
        return [Manager.PIPX, 'upgrade', package]

    if install.manager == Manager.UV:
        command = [Manager.UV, 'pip', 'install', '--python', sys.executable]
    else:
        command = [sys.executable, '-m', Manager.PIP, 'install']

    spec = _upgrade_spec(install, package, release)
    if install.editable:
        command += ['-e', spec]
    else:
        command.append(spec)
    if install.kind in (Kind.REGISTRY, Kind.VCS):
        command.append('--upgrade')
    return command


def format_command(command: list[str]) -> str:
    """Return a command rendered for display."""

    if sys.platform == 'win32':
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _upgrade_spec(install: Install, package: str, release: Release) -> str:
    """Return the package specifier to install for an install kind."""

    if install.kind in (Kind.GIT, Kind.SOURCE):
        return str(install.root)
    if install.kind == Kind.VCS:
        url = (install.url or '').removeprefix('git+')
        if release.tag:
            return f'{package} @ git+{url}@{release.tag}'
        return f'{package} @ git+{url}'
    return package


def _install_from_direct_url(
    dist: metadata.Distribution, manager: Manager
) -> Install | None:
    """Return the git, source or VCS install from a distribution's `direct_url.json`."""

    text = dist.read_text('direct_url.json')
    if text is None:
        return None
    try:
        direct = json.loads(text)
    except ValueError:
        return None
    if not isinstance(direct, dict):
        return None

    dir_info = direct.get('dir_info')
    if isinstance(dir_info, dict):
        root = _local_path(direct.get('url'))
        if root is not None:
            editable = bool(dir_info.get('editable', False))
            kind = Kind.GIT if (root / '.git').exists() else Kind.SOURCE
            return Install(kind=kind, root=root, manager=manager, editable=editable)

    vcs_info = direct.get('vcs_info')
    if isinstance(vcs_info, dict):
        return Install(
            kind=Kind.VCS,
            root=None,
            manager=manager,
            url=direct.get('url'),
        )

    return None


def _manager(dist: metadata.Distribution) -> Manager:
    """Return the manager that installed a distribution."""

    # A tool environment owns the whole prefix.
    parent = Path(sys.prefix).parent
    if parent.name == 'tools' and parent.parent.name == Manager.UV:
        return Manager.UV_TOOL
    if parent.name == 'venvs' and parent.parent.name == Manager.PIPX:
        return Manager.PIPX

    # Fall back to the installer recorded in the metadata.
    installer = (dist.read_text('INSTALLER') or '').strip().lower()
    if installer == Manager.UV:
        return Manager.UV
    if installer == Manager.PIP:
        return Manager.PIP
    if shutil.which(Manager.UV) is not None:
        return Manager.UV

    return Manager.PIP


def _local_path(url: str | None) -> Path | None:
    """Return the local path of a file URL."""

    if not url or not url.startswith('file://'):
        return None
    return Path(url2pathname(urlparse(url).path))
