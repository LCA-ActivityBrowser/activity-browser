# -*- coding: utf-8 -*-
"""Qt-free SHRECC Explorer session: data discovery, Prepare, server lifecycle."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol
from urllib.error import URLError
from urllib.request import urlopen


EXPLORER_SUBDIR = "explorer"
EXPORTS_SUBDIR = "exports"
CACHE_DIR_NAME = "consumption_results_v1"
ENV_EXPORTS_DIR = "EXPLORER_DATA_DIR"


def explorer_exports_dir(data_dir: Path) -> Path:
    return Path(data_dir) / EXPLORER_SUBDIR / EXPORTS_SUBDIR


def explorer_prepared_dir(data_dir: Path) -> Path:
    return Path(data_dir) / EXPLORER_SUBDIR / "prepared"


def resolve_data_dir(configured: str | None) -> Path:
    """Resolve Settings data directory or SHRECC / platform default."""
    text = (configured or "").strip()
    if text:
        return Path(text)
    try:
        from platformdirs import user_data_dir

        return Path(user_data_dir("shrecc", appauthor=False)) / "shrecc"
    except Exception:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "shrecc" / "shrecc"
        return Path.home() / ".local" / "share" / "shrecc" / "shrecc"


def find_consumption_caches(data_dir: Path) -> list[Path]:
    """Find SHRECC ``consumption_results_v1`` directories under the data root."""
    root = Path(data_dir)
    if not root.is_dir():
        return []
    found: list[Path] = []
    for manifest in root.rglob("manifest.json"):
        parent = manifest.parent
        if parent.name != CACHE_DIR_NAME:
            continue
        try:
            text = manifest.read_text(encoding="utf-8")
        except OSError:
            continue
        if "shrecc-consumption-results" not in text:
            continue
        found.append(parent)
    return sorted(found)


def list_ready_exports(data_dir: Path) -> list[Path]:
    exports = explorer_exports_dir(data_dir)
    if not exports.is_dir():
        return []
    return sorted(p for p in exports.glob("*.nc") if p.is_file())


@dataclass
class ExplorerStatus:
    data_dir: Path
    data_dir_ok: bool
    has_cache: bool
    ready_exports: list[Path] = field(default_factory=list)
    can_prepare: bool = False
    can_embed: bool = False
    message: str = ""


class PrepareRunner(Protocol):
    def __call__(self, data_dir: Path, export_dir: Path) -> list[Path]: ...


class ProcessFactory(Protocol):
    def __call__(self, command: list[str], *, env: dict[str, str], cwd: str | None) -> subprocess.Popen: ...


def default_prepare_runner(data_dir: Path, export_dir: Path) -> list[Path]:
    """Build explorer NetCDFs (and comparison summaries) from SHRECC caches."""
    from shrecc_explorer.comparison import prepare_comparison
    from shrecc_explorer.export_2025 import load_compact_export

    caches = find_consumption_caches(data_dir)
    if not caches:
        raise FileNotFoundError(f"No {CACHE_DIR_NAME} cache under {data_dir}")
    export_dir.mkdir(parents=True, exist_ok=True)
    explorer_prepared_dir(data_dir).mkdir(parents=True, exist_ok=True)
    previous = os.environ.get(ENV_EXPORTS_DIR)
    os.environ[ENV_EXPORTS_DIR] = str(export_dir)
    written: list[Path] = []
    try:
        for cache in caches:
            year_hint = cache.parent.name
            try:
                model_year = int(year_hint)
            except ValueError:
                model_year = 2025
            if model_year >= 2050:
                out = export_dir / "shrecc_de2050_cy2009_eu_countries.nc"
                scenario = "Distributed Energy"
                climate_year = 2009
            else:
                out = export_dir / "shrecc_2025_eu_countries.nc"
                scenario = "historical"
                climate_year = model_year
            dataset = load_compact_export(
                cache,
                model_year=model_year,
                scenario=scenario,
                climate_year=climate_year,
            )
            dataset.to_netcdf(out)
            written.append(out)
            try:
                prepare_comparison(
                    out,
                    factor_set="UNECE 2022 Europe + fossil GHG estimates",
                )
            except Exception:
                pass
    finally:
        if previous is None:
            os.environ.pop(ENV_EXPORTS_DIR, None)
        else:
            os.environ[ENV_EXPORTS_DIR] = previous
    return written


def _default_process_factory(
    command: list[str], *, env: dict[str, str], cwd: str | None
) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        env=env,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ExplorerSession:
    """Discover explorer data, run Prepare, and manage one localhost Streamlit server."""

    def __init__(
        self,
        *,
        data_dir_provider: Callable[[], Path | str | None],
        prepare_runner: PrepareRunner | None = None,
        process_factory: ProcessFactory | None = None,
        server_command: Callable[[int], list[str]] | None = None,
        health_timeout_s: float = 60.0,
    ):
        self._data_dir_provider = data_dir_provider
        self._prepare_runner = prepare_runner or default_prepare_runner
        self._process_factory = process_factory or _default_process_factory
        self._server_command = server_command or _default_server_command
        self._health_timeout_s = health_timeout_s
        self._process: Optional[subprocess.Popen] = None
        self._url: Optional[str] = None
        self.last_error: str = ""

    def resolved_data_dir(self) -> Path:
        raw = self._data_dir_provider()
        if isinstance(raw, Path):
            return raw
        return resolve_data_dir(None if raw is None else str(raw))

    def status(self) -> ExplorerStatus:
        data_dir = self.resolved_data_dir()
        ok = True
        message = ""
        if not data_dir.exists():
            ok = False
            message = f"Data directory does not exist: {data_dir}"
        elif not data_dir.is_dir():
            ok = False
            message = f"Data directory is not a folder: {data_dir}"
        caches = find_consumption_caches(data_dir) if ok else []
        exports = list_ready_exports(data_dir) if ok else []
        has_cache = bool(caches)
        can_embed = bool(exports)
        can_prepare = ok and has_cache
        if ok and not message:
            if can_embed:
                message = f"{len(exports)} explorer dataset(s) ready under {explorer_exports_dir(data_dir)}"
            elif can_prepare:
                message = "SHRECC cache found. Run Prepare to build explorer datasets."
            else:
                message = (
                    "Nothing to explore yet. Add SHRECC cache under the data directory, "
                    "then run Prepare."
                )
        return ExplorerStatus(
            data_dir=data_dir,
            data_dir_ok=ok,
            has_cache=has_cache,
            ready_exports=exports,
            can_prepare=can_prepare,
            can_embed=can_embed,
            message=message,
        )

    def run_prepare(self) -> list[Path]:
        data_dir = self.resolved_data_dir()
        export_dir = explorer_exports_dir(data_dir)
        written = list(self._prepare_runner(data_dir, export_dir))
        return written

    def ensure_server(self) -> str:
        status = self.status()
        if not status.can_embed:
            raise RuntimeError(
                status.message or "No explorer-ready datasets; Prepare first."
            )
        if self._url and self._process is not None and self._process.poll() is None:
            return self._url
        self.stop_server()
        port = _free_port()
        exports = explorer_exports_dir(status.data_dir)
        env = os.environ.copy()
        env[ENV_EXPORTS_DIR] = str(exports)
        command = self._server_command(port)
        try:
            self._process = self._process_factory(
                command, env=env, cwd=str(exports.parent)
            )
        except OSError as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Failed to start explorer: {exc}") from exc
        url = f"http://127.0.0.1:{port}"
        if not self._wait_healthy(url):
            err = self.last_error or "Explorer server did not become ready."
            self.stop_server()
            raise RuntimeError(err)
        self._url = url
        return url

    def server_url(self) -> str | None:
        return self._url

    def stop_server(self) -> None:
        proc = self._process
        self._process = None
        self._url = None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _wait_healthy(self, url: str) -> bool:
        deadline = time.monotonic() + self._health_timeout_s
        health = url.rstrip("/") + "/_stcore/health"
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                stderr = ""
                if self._process.stderr is not None:
                    try:
                        stderr = self._process.stderr.read().decode("utf-8", "replace")
                    except Exception:
                        stderr = ""
                self.last_error = stderr.strip() or "Explorer process exited early."
                return False
            try:
                with urlopen(health, timeout=1) as response:  # noqa: S310 — localhost only
                    if response.status == 200:
                        return True
            except (URLError, OSError):
                pass
            time.sleep(0.2)
        self.last_error = "Timed out waiting for explorer health check."
        return False


def _default_server_command(port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "shrecc_explorer.streamlit_entry",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
