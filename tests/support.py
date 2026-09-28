import json
from typing import Any

from qt_updater.core import Release, ReleaseProvider


class FakeDistribution:
    def __init__(
        self,
        direct_url: dict[str, Any] | None = None,
        installer: str = 'pip',
    ) -> None:
        self._direct_url = direct_url
        self._installer = installer

    def read_text(self, filename: str) -> str | None:
        if filename == 'direct_url.json':
            if self._direct_url is None:
                return None
            return json.dumps(self._direct_url)
        if filename == 'INSTALLER':
            return self._installer
        return None


class FakeProvider(ReleaseProvider):
    def __init__(self, release: Release | None = None) -> None:
        self._release = release

    def latest(self) -> Release | None:
        return self._release


class FakeResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._data


class FakeSession:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> FakeResponse:
        self.calls.append((url, headers))
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise RuntimeError(f'no response for {url}')
        return self._response


def make_release(
    version: str = '2.0.0',
    tag: str = '',
    source_url: str = '',
) -> Release:
    return Release(tag=tag or f'v{version}', source_url=source_url)
