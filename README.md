# Qt Updater

Check for and apply updates to a Qt application, with a dialog that streams the
update as a subprocess.

## Installation

Use as a dependency in `pyproject.toml`:

```toml
[project]
dependencies = [
    "qt-updater@git+https://github.com/beatreichenbach/qt-updater",
]
```

## Usage

Describe the application and check for a newer release using the UI:

```python
from qt_updater import App, show_update_dialog

app = App.github(package='openbridge', repository='beatreichenbach/openbridge')
show_update_dialog(app)
```

Or with a custom implementation:

```python
from qt_updater import App, update

app = App.github(package='openbridge', repository='beatreichenbach/openbridge')
update(app)
```

## Supported install types

The updater detects how the host was installed from the distribution's PEP 610 `direct_url.json` and `INSTALLER`,
then updates from the release tag:

| Install                | Update                                                       |
|------------------------|--------------------------------------------------------------|
| `git clone` + install  | fetch tags, hard reset to the release tag, reinstall         |
| zip download + install | download the release source zip, replace the tree, reinstall |
| `uv pip / pip`         | `uv pip`/`pip install --upgrade`                             |
| `uv tool` / `pipx`     | `uv tool upgrade` / `pipx upgrade`                           |

> [!NOTE]
> For the zip case the provider picks the release's source archive: the first uploaded asset ending in `.zip`,
> otherwise GitHub's auto-generated source zip.
>
> The package manager (`pip` or `uv`) is taken from the installed distribution.
> Updates always target a tagged release, never a branch tip.

## Custom providers

Only GitHub is supported out of the box.
To add another host, subclass the `ReleaseProvider` base and pass it to `App`:

```python
from qt_updater import App, Release, ReleaseProvider


class GitLabProvider(ReleaseProvider):
    def __init__(self, repository: str) -> None:
        self.repository = repository

    def latest(self) -> Release | None: ...


app = App(package='package', provider=GitLabProvider('owner/repository'))
```

## Development

```sh
uv venv --python 3.11
uv pip install -e ".[dev]"
pre-commit install
```

Run the checks:

```sh
ruff format .
ruff check --select I --fix .
ruff check .
ty check
pytest
```

The dialog icons in `qt_updater/ui/qt_material_icons` are generated with:

```sh
uv run qtmaterialicons -o qt_updater/ui --styles outlined --sizes 20 --names check error pending system_update_alt
```

## License

Copyright (c) 2026 Beat Reichenbach. This project is licensed under the [GPLv3 License](LICENSE).
