from __future__ import annotations

import dataclasses
from importlib import metadata

from .providers import GitHubProvider, ReleaseProvider


@dataclasses.dataclass(frozen=True)
class App:
    package: str
    provider: ReleaseProvider
    version: str = ''

    def __post_init__(self) -> None:
        if not self.version:
            try:
                version = metadata.version(self.package)
            except metadata.PackageNotFoundError:
                version = '0'
            object.__setattr__(self, 'version', version)

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
            provider=GitHubProvider(repository, token=token),
            version=version,
        )
