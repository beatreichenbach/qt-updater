import logging
import os
from typing import Any

import requests

from .. import models
from . import base

logger = logging.getLogger(__name__)

API = 'https://api.github.com'
TIMEOUT = 10


class GitHubProvider(base.ReleaseProvider):
    """
    Read releases from GitHub.

    The repository is an ``owner/name`` slug.
    The token falls back to the ``GITHUB_TOKEN`` or ``GH_TOKEN`` environment variables.
    """

    def __init__(
        self,
        repository: str,
        token: str | None = None,
        timeout: int = TIMEOUT,
    ) -> None:
        self.repository = repository
        self.token = (
            token or os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
        )
        self.session = requests.Session()
        self.timeout = timeout

    def latest(self) -> models.Release | None:
        """Return the latest published release."""

        return self._get(f'/repos/{self.repository}/releases/latest')

    def _get(self, path: str) -> models.Release | None:
        try:
            response = self.session.get(
                f'{API}{path}', headers=self._headers(), timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            logger.error(f'Could not read release {path}: {error}')
            return None
        return parse_release(data)

    def _headers(self) -> dict[str, str]:
        headers = {'Accept': 'application/vnd.github+json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers


def parse_release(data: dict[str, Any]) -> models.Release:
    """Return a release parsed from a GitHub API response."""

    source_url = str(data.get('zipball_url') or '')
    for asset in data.get('assets') or ():
        name = str(asset.get('name') or '')
        if name.endswith('.zip'):
            source_url = str(asset.get('browser_download_url') or '')
            break

    tag = str(data.get('tag_name') or '')
    return models.Release(tag=tag, source_url=source_url)
