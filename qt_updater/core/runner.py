import dataclasses
import logging
import subprocess
import sys
from pathlib import Path

from .exceptions import UpdaterError
from .models import App, Release, has_update

SCRIPT = Path(__file__).with_name('updater.py')


logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CheckResult:
    release: Release | None = None
    error: str | None = None

    @property
    def available(self) -> bool:
        return self.release is not None

    @property
    def up_to_date(self) -> bool:
        return self.release is None and self.error is None

    @property
    def failed(self) -> bool:
        return self.error is not None


def check(app: App) -> CheckResult:
    """
    Check an app for a newer release.

    A version that cannot be compared is reported as an error rather than as
    being up to date.
    """

    error = f'Could not check for updates for {app.package}.'
    try:
        release = app.provider.latest()
    except UpdaterError as failure:
        logger.error(f'{error} {failure}')
        return CheckResult(error=error)

    if release is None:
        logger.error(error)
        return CheckResult(error=error)

    try:
        newer = has_update(app.version, release.version)
    except ValueError as failure:
        return CheckResult(error=str(failure))

    if newer:
        return CheckResult(release=release)
    return CheckResult()


def update(app: App, release: Release | None = None) -> int:
    """Run the update in a subprocess and return its exit code."""

    if release is None:
        result = check(app)
        if result.release is None:
            if result.error:
                print(f'error: {result.error}', flush=True)
            else:
                print('No update available.', flush=True)
            return 0
        release = result.release

    return subprocess.run(command(app.package, release)).returncode


def command(package: str, release: Release) -> list[str]:
    """Return the command that runs an update."""

    return [
        sys.executable,
        str(SCRIPT),
        package,
        release.tag,
        release.source_url,
    ]
