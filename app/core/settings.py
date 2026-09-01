"""Load, validate, and persist RigLog application settings."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping

from app.core.app_paths import get_app_paths
from app.core.modules import (
    DEFAULT_ENABLED_MODULE_KEYS,
    normalise_enabled_module_keys,
)
from app.core.report_sections import (
    get_default_report_section_keys,
    normalise_report_section_keys,
)

DEFAULT_STEP_TARGET = 10_000

KNOWN_SETTING_KEYS = {
    "setup_complete",
    "enabled_modules",
    "step_target",
    "pdf_report_section_keys",
}


@dataclass(slots=True)
class AppSettings:
    """Validated user-configurable RigLog settings."""

    setup_complete: bool = True
    enabled_modules: tuple[str, ...] = DEFAULT_ENABLED_MODULE_KEYS
    step_target: int = DEFAULT_STEP_TARGET
    pdf_report_section_keys: tuple[str, ...] = field(default_factory=tuple)
    extra_settings: dict[str, Any] = field(
        default_factory=dict,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Normalise settings that depend on the enabled-module list."""
        self.enabled_modules = normalise_enabled_module_keys(
            self.enabled_modules
        )

        default_pdf_section_keys = get_default_report_section_keys(
            self.enabled_modules,
            export_kind="pdf",
        )

        if not self.pdf_report_section_keys:
            self.pdf_report_section_keys = default_pdf_section_keys
            return

        normalised_pdf_section_keys = normalise_report_section_keys(
            self.pdf_report_section_keys,
            self.enabled_modules,
            export_kind="pdf",
        )

        self.pdf_report_section_keys = (
            normalised_pdf_section_keys
            if normalised_pdf_section_keys
            else default_pdf_section_keys
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the settings."""
        payload = dict(self.extra_settings)
        payload.update(
            {
                "setup_complete": self.setup_complete,
                "enabled_modules": list(self.enabled_modules),
                "step_target": self.step_target,
                "pdf_report_section_keys": list(self.pdf_report_section_keys),
            }
        )
        return payload


def get_default_settings() -> AppSettings:
    """Return settings that preserve the current full RigLog experience."""
    return AppSettings()


def _resolve_settings_file(
    settings_file: str | Path | None,
) -> Path:
    """Resolve an explicit or default settings-file path."""
    if settings_file is not None:
        return Path(settings_file).expanduser().resolve()

    return get_app_paths().settings_file


def _normalise_setup_complete(
    value: Any,
    *,
    default: bool,
) -> bool:
    """Return a valid setup-completion flag."""
    if isinstance(value, bool):
        return value

    return default


def _normalise_step_target(
    value: Any,
    *,
    default: int,
) -> int:
    """Return a valid positive step target."""
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    ):
        return value

    return default


def _normalise_enabled_modules(
    value: Any,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Return valid module keys in stable application order."""
    if not isinstance(value, (list, tuple)):
        return default

    try:
        return normalise_enabled_module_keys(value)
    except ValueError:
        return default


def _normalise_pdf_report_section_keys(
    value: Any,
    *,
    enabled_module_keys: tuple[str, ...],
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Return valid PDF report-section keys in registry order."""
    if not isinstance(value, (list, tuple)):
        return default

    normalised_keys = normalise_report_section_keys(
        value,
        enabled_module_keys,
        export_kind="pdf",
    )

    return normalised_keys or default


def settings_from_mapping(
    payload: Mapping[str, Any],
) -> AppSettings:
    """Build validated application settings from mapping-like data."""
    defaults = get_default_settings()

    extra_settings = {
        key: value
        for key, value in payload.items()
        if key not in KNOWN_SETTING_KEYS
    }

    enabled_modules = _normalise_enabled_modules(
    payload.get("enabled_modules"),
    default=defaults.enabled_modules,
)
    default_pdf_section_keys = get_default_report_section_keys(
        enabled_modules,
        export_kind="pdf",
    )

    return AppSettings(
        setup_complete=_normalise_setup_complete(
            payload.get("setup_complete"),
            default=defaults.setup_complete,
        ),
        enabled_modules=enabled_modules,
        step_target=_normalise_step_target(
            payload.get("step_target"),
            default=defaults.step_target,
        ),
        pdf_report_section_keys=_normalise_pdf_report_section_keys(
            payload.get("pdf_report_section_keys"),
            enabled_module_keys=enabled_modules,
            default=default_pdf_section_keys,
        ),
        extra_settings=extra_settings,
    )


def load_settings(
    settings_file: str | Path | None = None,
) -> AppSettings:
    """Load settings, returning safe defaults when reading fails.

    Missing, malformed, unreadable, or structurally invalid settings files
    do not prevent RigLog from starting.
    """
    path = _resolve_settings_file(settings_file)

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ):
        return get_default_settings()

    if not isinstance(payload, dict):
        return get_default_settings()

    return settings_from_mapping(payload)


def save_settings(
    settings: AppSettings,
    settings_file: str | Path | None = None,
) -> None:
    """Validate and atomically save application settings.

    The temporary file is created in the destination directory so
    ``os.replace`` remains an atomic filesystem operation.
    """
    path = _resolve_settings_file(settings_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    validated_settings = settings_from_mapping(settings.to_dict())
    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            json.dump(
                validated_settings.to_dict(),
                temporary_file,
                indent=2,
                sort_keys=True,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def should_show_setup(
    settings: AppSettings,
) -> bool:
    """Return whether first-run setup should be displayed."""
    return not settings.setup_complete
