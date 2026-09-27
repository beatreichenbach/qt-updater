# Qt Updater

Update interface for Qt applications.

## Installation

Use as a dependency in `pyproject.toml`:

```toml
[project]
dependencies = [
    "qt-updater@git+https://github.com/beatreichenbach/qt-updater",
]
```

## Usage

Show the update dialog from a Qt application:

```python
from qt_updater import show_update_dialog

show_update_dialog(parent)
```

A standalone runner is also available:

```sh
python -m qt_updater.updater
```

## Development

```sh
uv venv --python 3.11
uv pip install -e ".[dev]"
pre-commit install
```

Run the checks:

```sh
uv run ruff format qt_updater tests
uv run ruff check --select I --fix qt_updater tests
uv run ruff check qt_updater tests
uv run ty check qt_updater
uv run pytest
```

## License

Copyright (c) 2026 Beat Reichenbach. This project is licensed under the [GPLv3 License](LICENSE).
