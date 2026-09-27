import dataclasses
from importlib import metadata

from packaging.version import InvalidVersion, Version

from . import providers


@dataclasses.dataclass(frozen=True)
class App:
    package: str
    provider: providers.ReleaseProvider
    version: str = ''

    def __post_init__(self) -> None:
        if not self.version:
            object.__setattr__(self, 'version', current_version(self.package))

    @classmethod
    def github(
        cls,
        package: str,
        repository: str,
        version: str = '',
        token: str | None = None,
    ) -> App:
        """Build an app that checks GitHub releases."""

        return cls(
            package=package,
            provider=providers.GitHubProvider(repository, token=token),
            version=version,
        )


def current_version(package: str) -> str:
    """Return the installed version of a package."""

    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return '0'


@dataclasses.dataclass(frozen=True)
class Release:
    tag: str
    source_url: str = ''

    @property
    def version(self) -> str:
        return self.tag.removeprefix('v').removeprefix('V')


def has_update(current: str, latest: str) -> bool:
    """
    Return whether a version is newer than the current version.

    :raises InvalidVersion: if a version cannot be parsed.
    """

    try:
        return Version(latest) > Version(current)
    except InvalidVersion as error:
        raise InvalidVersion(f'cannot compare {current!r} with {latest!r}') from error
