import dataclasses

from packaging.version import InvalidVersion, Version


@dataclasses.dataclass(frozen=True)
class Release:
    tag: str
    source_url: str = ''

    @property
    def version(self) -> str:
        return self.tag.removeprefix('v').removeprefix('V')

    def is_newer_than(self, version: str) -> bool:
        """
        Return whether this release is newer than a version.

        :raises InvalidVersion: if a version cannot be parsed.
        """

        try:
            return Version(self.version) > Version(version)
        except InvalidVersion as error:
            raise InvalidVersion(
                f'cannot compare {self.version!r} with {version!r}'
            ) from error
