# -*- coding: utf-8 -*-
"""Qt-free SHRECC Explorer session: discover data, Prepare, one Streamlit process."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.error import URLError
from urllib.request import urlopen

CACHE_NAME = "consumption_results_v1"
ENV_EXPORTS = "EXPLORER_DATA_DIR"


def explorer_exports_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "explorer" / "exports"


def explorer_prepared_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "explorer" / "prepared"


def resolve_data_dir(configured: str | None) -> Path:
    text = (configured or "").strip()
    if text:
        return Path(text)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "shrecc" / "shrecc"
    return Path.home() / ".local" / "share" / "shrecc" / "shrecc"


def find_consumption_caches(data_dir: Path) -> list[Path]:
    root = Path(data_dir)
    if not root.is_dir():
        return []
    found = []
    for manifest in root.rglob("manifest.json"):
        if manifest.parent.name != CACHE_NAME:
            continue
        try:
            if "shrecc-consumption-results" in manifest.read_text(encoding="utf-8"):
                found.append(manifest.parent)
        except OSError:
            continue
    return sorted(found)


def list_ready_exports(data_dir: Path) -> list[Path]:
    folder = explorer_exports_dir(data_dir)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.nc") if p.is_file())


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def exports_need_prepare(caches: list[Path], exports: list[Path]) -> bool:
    if not caches:
        return False
    if not exports:
        return True
    cache_mtime = max(_mtime(c / "manifest.json") for c in caches)
    export_mtime = max(_mtime(p) for p in exports)
    return cache_mtime > export_mtime


@dataclass
class ExplorerStatus:
    data_dir: Path
    data_dir_ok: bool
    has_cache: bool
    ready_exports: list[Path] = field(default_factory=list)
    can_prepare: bool = False
    can_embed: bool = False
    prepare_is_refresh: bool = False
    message: str = ""


def default_prepare_runner(data_dir: Path, export_dir: Path) -> list[Path]:
    from shrecc_explorer.comparison import prepare_comparison
    from shrecc_explorer.export_2025 import load_compact_export

    caches = find_consumption_caches(data_dir)
    if not caches:
        raise FileNotFoundError(f"No {CACHE_NAME} cache under {data_dir}")

    export_dir.mkdir(parents=True, exist_ok=True)
    explorer_prepared_dir(data_dir).mkdir(parents=True, exist_ok=True)
    prev = os.environ.get(ENV_EXPORTS)
    os.environ[ENV_EXPORTS] = str(export_dir)
    written: list[Path] = []
    try:
        for cache in caches:
            try:
                model_year = int(cache.parent.name)
            except ValueError:
                model_year = 2025
            if model_year >= 2050:
                out = export_dir / "shrecc_de2050_cy2009_eu_countries.nc"
                dataset = load_compact_export(
                    cache,
                    model_year=model_year,
                    scenario="Distributed Energy",
                    climate_year=2009,
                )
            else:
                out = export_dir / "shrecc_2025_eu_countries.nc"
                dataset = load_compact_export(
                    cache,
                    model_year=model_year,
                    scenario="historical",
                    climate_year=model_year,
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
        if prev is None:
            os.environ.pop(ENV_EXPORTS, None)
        else:
            os.environ[ENV_EXPORTS] = prev
    return written


class ExplorerSession:
    def __init__(
        self,
        *,
        data_dir_provider: Callable[[], Path | str | None],
        prepare_runner: Callable[[Path, Path], list[Path]] | None = None,
        process_factory: Callable[..., subprocess.Popen] | None = None,
        health_timeout_s: float = 60.0,
    ):
        self._data_dir_provider = data_dir_provider
        self._prepare = prepare_runner or default_prepare_runner
        self._popen = process_factory or subprocess.Popen
        self._health_timeout_s = health_timeout_s
        self._proc: Optional[subprocess.Popen] = None
        self._url: Optional[str] = None
        self.last_error = ""
        self._flash = ""  # one-shot status after Prepare

    def resolved_data_dir(self) -> Path:
        raw = self._data_dir_provider()
        if isinstance(raw, Path):
            return raw
        return resolve_data_dir(None if raw is None else str(raw))

    def status(self) -> ExplorerStatus:
        data_dir = self.resolved_data_dir()
        ok = data_dir.is_dir()
        if not data_dir.exists():
            return ExplorerStatus(
                data_dir, False, False, message=f"Data directory does not exist: {data_dir}"
            )
        if not ok:
            return ExplorerStatus(
                data_dir, False, False, message=f"Data directory is not a folder: {data_dir}"
            )

        caches = find_consumption_caches(data_dir)
        exports = list_ready_exports(data_dir)
        needs = exports_need_prepare(caches, exports)
        embed = bool(exports)
        flash, self._flash = self._flash, ""

        if embed and not needs:
            message = flash
        elif embed and needs:
            message = "Cache is newer than explorer data. Click Refresh to rebuild."
        elif needs:
            message = "SHRECC cache found. Run Prepare to build explorer datasets."
        else:
            message = "Nothing to explore yet. Add SHRECC cache, then run Prepare."

        return ExplorerStatus(
            data_dir=data_dir,
            data_dir_ok=True,
            has_cache=bool(caches),
            ready_exports=exports,
            can_prepare=needs,
            can_embed=embed,
            prepare_is_refresh=needs and embed,
            message=message,
        )

    def run_prepare(self) -> list[Path]:
        data_dir = self.resolved_data_dir()
        written = list(self._prepare(data_dir, explorer_exports_dir(data_dir)))
        self._flash = f"Prepared {len(written)} dataset(s)." if written else "Prepare finished."
        self.stop_server()
        return written

    def ensure_server(self) -> str:
        st = self.status()
        if not st.can_embed:
            raise RuntimeError(st.message or "Prepare explorer datasets first.")
        if self._url and self._proc is not None and self._proc.poll() is None:
            return self._url

        self.stop_server()
        port = self._free_port()
        exports = explorer_exports_dir(st.data_dir)
        env = {**os.environ, ENV_EXPORTS: str(exports)}
        cmd = [
            sys.executable,
            "-m",
            "shrecc_explorer.streamlit_entry",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
        try:
            self._proc = self._popen(
                cmd,
                env=env,
                cwd=str(exports.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
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

    def stop_server(self) -> None:
        proc, self._proc, self._url = self._proc, None, None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _wait_healthy(self, url: str) -> bool:
        health = url.rstrip("/") + "/_stcore/health"
        deadline = time.monotonic() + self._health_timeout_s
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                err = ""
                if self._proc.stderr is not None:
                    try:
                        err = self._proc.stderr.read().decode("utf-8", "replace")
                    except Exception:
                        pass
                self.last_error = err.strip() or "Explorer process exited early."
                return False
            try:
                with urlopen(health, timeout=1) as resp:  # noqa: S310
                    if resp.status == 200:
                        return True
            except (URLError, OSError):
                pass
            time.sleep(0.2)
        self.last_error = "Timed out waiting for explorer health check."
        return False
