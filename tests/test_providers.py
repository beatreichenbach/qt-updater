import pytest
import requests
from support import FakeResponse, FakeSession

from qt_updater.core import GitHubProvider
from qt_updater.core.providers import github
from qt_updater.core.providers.github import parse_release

PAYLOAD = {
    'tag_name': 'v1.2.0',
    'zipball_url': 'https://example.com/source.zip',
    'assets': [
        {
            'name': 'app-1.2.0-data.zip',
            'browser_download_url': 'https://ex.com/app-data.zip',
        },
        {
            'name': 'app-1.2.0.whl',
            'browser_download_url': 'https://ex.com/app.whl',
        },
    ],
}


def test_parse_release_prefers_uploaded_zip() -> None:
    release = parse_release(PAYLOAD)

    assert release.tag == 'v1.2.0'
    assert release.version == '1.2.0'
    assert release.source_url == 'https://ex.com/app-data.zip'


def test_parse_release_falls_back_to_source() -> None:
    data = {
        'tag_name': 'v1.2.0',
        'zipball_url': 'https://example.com/source.zip',
        'assets': [
            {'name': 'app-1.2.0.whl', 'browser_download_url': 'https://ex.com/app.whl'}
        ],
    }

    assert parse_release(data).source_url == 'https://example.com/source.zip'


def patch_session(monkeypatch: pytest.MonkeyPatch, session: FakeSession) -> None:
    monkeypatch.setattr(github.requests, 'Session', lambda: session)


def test_latest_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(FakeResponse(PAYLOAD))
    patch_session(monkeypatch, session)

    provider = GitHubProvider('acme/app')

    release = provider.latest()

    assert release is not None
    assert release.version == '1.2.0'
    assert session.calls[0][0].endswith('/repos/acme/app/releases/latest')


def test_latest_sends_token(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(FakeResponse(PAYLOAD))
    patch_session(monkeypatch, session)

    provider = GitHubProvider('acme/app', token='secret')

    provider.latest()

    assert session.calls[0][1] is not None
    assert session.calls[0][1].get('Authorization') == 'Bearer secret'


def test_latest_returns_none_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(error=requests.RequestException('boom'))
    patch_session(monkeypatch, session)

    provider = GitHubProvider('acme/app')

    assert provider.latest() is None
