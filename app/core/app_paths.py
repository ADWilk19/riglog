"""Cross-platform filesystem locations for writable RigLog data."""

from dataclasses import dataclass
import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths


APP_DIRECTORY_NAME = "RigLog"
DATA_DIR_ENV_VAR = "RIGLOG_DATA_DIR"

SETTINGS_FILENAME = "settings.json"
DATABASE_FILENAME = "riglog.db"
FITBIT_TOKENS_FILENAME = "fitbit_tokens.json"
EXPORTS_DIRECTORY_NAME = "exports"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Resolved writable filesystem locations used by RigLog."""

    data_dir: Path
    settings_file: Path
    database_file: Path
    fitbit_tokens_file: Path
    exports_dir: Path

    def ensure_directories(self) -> None:
        """Create the writable application directories when required."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)


def _normalise_path(path: str | Path) -> Path:
    """Expand and resolve a filesystem path."""
    return Path(path).expanduser().resolve()


def _get_qt_data_root() -> Path:
    """Return Qt's platform-appropriate generic writable data directory."""
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericDataLocation
    )

    if not location:
        raise RuntimeError(
            "Qt could not resolve a writable application data directory."
        )

    return _normalise_path(location)


def get_app_data_dir(
    base_dir: str | Path | None = None,
) -> Path:
    """Resolve the writable RigLog application-data directory.

    Resolution precedence:

    1. Explicit ``base_dir`` argument.
    2. ``RIGLOG_DATA_DIR`` environment variable.
    3. Qt's platform-appropriate generic data directory plus ``RigLog``.

    Args:
        base_dir: Optional explicit directory, primarily useful for tests,
            development, or controlled application launches.
    """
    if base_dir is not None:
        return _normalise_path(base_dir)

    environment_dir = os.getenv(DATA_DIR_ENV_VAR)

    if environment_dir and environment_dir.strip():
        return _normalise_path(environment_dir)

    return _get_qt_data_root() / APP_DIRECTORY_NAME


def get_app_paths(
    base_dir: str | Path | None = None,
    *,
    create: bool = False,
) -> AppPaths:
    """Build the writable path contract used by RigLog.

    Args:
        base_dir: Optional application-data directory override.
        create: Whether to create the data and export directories.

    Returns:
        Resolved application paths.
    """
    data_dir = get_app_data_dir(base_dir)

    paths = AppPaths(
        data_dir=data_dir,
        settings_file=data_dir / SETTINGS_FILENAME,
        database_file=data_dir / DATABASE_FILENAME,
        fitbit_tokens_file=data_dir / FITBIT_TOKENS_FILENAME,
        exports_dir=data_dir / EXPORTS_DIRECTORY_NAME,
    )

    if create:
        paths.ensure_directories()

    return paths
