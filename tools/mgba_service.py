#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scenario_inputs import condition_matches


MGBA_COMMIT = '5157ce208a5965e8a47bf5b48b5aae5198c22a5e'
PROTOCOL = 'gbre.mgba.v1'


class MgbaServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ServicePaths:
    directory: Path
    ready: Path
    log: Path
    captures: Path


def rom_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))
        return int(probe.getsockname()[1])


class MgbaService:
    def __init__(self, gbre_root: Path, rom: Path, expected_sha1: str,
                 *, runtime_root: Path | None = None, timeout: float = 5.0,
                 executable: Path | None = None, adapter: Path | None = None):
        self.gbre_root = gbre_root.resolve()
        self.rom = rom.resolve()
        self.expected_sha1 = expected_sha1.lower()
        self.runtime_root = (runtime_root or self.gbre_root / 'build/live').resolve()
        self.timeout = timeout
        self.executable = (executable or self.gbre_root /
                           '.cache/mgba/build-headless/mgba-headless').resolve()
        self.adapter = (adapter or self.gbre_root /
                        'oracle/tetris_observation.lua').resolve()
        self.paths: ServicePaths | None = None
        self.process: subprocess.Popen[str] | None = None
        self.socket: socket.socket | None = None
        self.reader = None
        self.log_file = None
        self.request_id = 0

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _validate_launch(self) -> None:
        if not self.rom.is_file():
            raise MgbaServiceError(f'ROM does not exist: {self.rom}')
        actual = rom_sha1(self.rom)
        if actual != self.expected_sha1:
            raise MgbaServiceError(
                f'ROM SHA-1 {actual} does not match {self.expected_sha1}'
            )
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise MgbaServiceError(
                f'pinned headless mGBA is missing: {self.executable}; '
                'run scripts/bootstrap-mgba-oracle.sh'
            )
        if not self.adapter.is_file():
            raise MgbaServiceError(f'observation adapter is missing: {self.adapter}')

    def start(self) -> dict[str, Any]:
        if self.running:
            raise MgbaServiceError('mGBA service is already running')
        self._validate_launch()
        stamp = f'{os.getpid()}-{time.time_ns()}'
        directory = self.runtime_root / stamp
        captures = directory / 'captures'
        captures.mkdir(parents=True)
        self.paths = ServicePaths(
            directory=directory,
            ready=directory / 'ready',
            log=directory / 'mgba.log',
            captures=captures,
        )
        port = available_port()
        environment = os.environ.copy()
        environment.update({
            'GBRE_SERVICE_PORT': str(port),
            'GBRE_SERVICE_READY': str(self.paths.ready),
            'GBRE_SERVICE_ADAPTER': str(
                self.adapter),
            'GBRE_SERVICE_ROM_SHA1': self.expected_sha1,
            'GBRE_SERVICE_MGBA_BUILD': MGBA_COMMIT,
        })
        self.log_file = self.paths.log.open('w')
        command = [
            str(self.executable),
            '-C', 'idleOptimization=none',
            '-C', 'logLevel=0',
            '--script', str(self.gbre_root / 'oracle/tetris_service.lua'),
            str(self.rom),
        ]
        self.process = subprocess.Popen(
            command, cwd=self.gbre_root, env=environment, text=True,
            stdout=self.log_file, stderr=subprocess.STDOUT,
        )
        try:
            self._wait_for_ready()
            self._connect(port)
            hello = self.command('hello')
            if hello.get('protocol') != PROTOCOL:
                raise MgbaServiceError(
                    f'unsupported mGBA protocol {hello.get("protocol")!r}'
                )
            if hello.get('rom_sha1') != self.expected_sha1:
                raise MgbaServiceError('mGBA service reported the wrong ROM')
            if hello.get('mgba_build') != MGBA_COMMIT:
                raise MgbaServiceError('mGBA service reported the wrong build')
            self.pause()
            return hello
        except Exception:
            self.stop(force=True)
            raise

    def _wait_for_ready(self) -> None:
        assert self.paths is not None
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._check_process()
            if self.paths.ready.is_file():
                return
            time.sleep(0.01)
        raise MgbaServiceError(
            f'timed out waiting for mGBA service; log: {self.paths.log}'
        )

    def _connect(self, port: int) -> None:
        deadline = time.monotonic() + self.timeout
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            self._check_process()
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(min(0.25, self.timeout))
            try:
                connection.connect(('127.0.0.1', port))
                connection.settimeout(self.timeout)
                self.socket = connection
                self.reader = connection.makefile('r', encoding='utf-8', newline='\n')
                return
            except OSError as error:
                last_error = error
                connection.close()
                time.sleep(0.01)
        raise MgbaServiceError(f'could not connect to mGBA service: {last_error}')

    def _check_process(self) -> None:
        if self.process is None:
            raise MgbaServiceError('mGBA service was not started')
        returncode = self.process.poll()
        if returncode is not None:
            log = self.paths.log if self.paths else '<unknown>'
            raise MgbaServiceError(
                f'mGBA service exited with status {returncode}; log: {log}'
            )

    def command(self, name: str, *arguments: object) -> dict[str, Any]:
        self._check_process()
        if self.socket is None or self.reader is None:
            raise MgbaServiceError('mGBA service is not connected')
        if '\t' in name or '\n' in name:
            raise ValueError('invalid protocol command')
        texts = [str(argument) for argument in arguments]
        if any('\t' in value or '\n' in value for value in texts):
            raise ValueError('protocol arguments may not contain tabs or newlines')
        self.request_id += 1
        request_id = self.request_id
        request = '\t'.join((str(request_id), name, *texts)) + '\n'
        try:
            self.socket.sendall(request.encode())
            line = self.reader.readline()
        except (OSError, TimeoutError) as error:
            self._check_process()
            raise MgbaServiceError(f'mGBA {name} request failed: {error}') from error
        if not line:
            self._check_process()
            raise MgbaServiceError(f'mGBA disconnected during {name}')
        try:
            result = json.loads(line)
        except json.JSONDecodeError as error:
            raise MgbaServiceError(f'mGBA returned invalid JSON: {line!r}') from error
        if result.get('id') != request_id:
            raise MgbaServiceError(
                f'mGBA response id {result.get("id")} did not match {request_id}'
            )
        if not result.get('ok'):
            raise MgbaServiceError(f'mGBA {name}: {result.get("error", "unknown error")}')
        return result

    def pause(self) -> dict[str, Any]:
        return self.command('pause')

    def run(self) -> dict[str, Any]:
        return self.command('run')

    def step(self, frames: int = 1) -> dict[str, Any]:
        if frames <= 0:
            raise ValueError('step frames must be positive')
        return self.command('step', frames)

    def reset(self) -> dict[str, Any]:
        return self.command('reset')

    def set_keys(self, mask: int) -> dict[str, Any]:
        if not 0 <= mask <= 0xFF:
            raise ValueError('Game Boy key mask must be in 0..255')
        return self.command('keys', mask)

    def read(self, address: int, count: int = 1) -> list[int]:
        return list(self.command('read', address, count)['values'])

    def write(self, address: int, value: int) -> dict[str, Any]:
        return self.command('write', address, value)

    def apply_patches(self, patches: Iterable[tuple[int, int]]) -> None:
        for address, value in patches:
            self.write(address, value)

    def observe(self) -> dict[str, Any]:
        return dict(self.command('observe')['observation'])

    def capture(self, name: str = 'framebuffer.png') -> Path:
        assert self.paths is not None
        if Path(name).name != name or not name.endswith('.png'):
            raise ValueError('capture name must be a plain .png filename')
        path = self.paths.captures / name
        result = self.command('capture', path)
        if result.get('width') != 160 or result.get('height') != 144:
            raise MgbaServiceError('mGBA returned an unexpected framebuffer size')
        if not path.is_file():
            raise MgbaServiceError(f'mGBA did not write framebuffer: {path}')
        return path

    def capture_raw(self, name: str = 'framebuffer.rgba') -> Path:
        assert self.paths is not None
        if Path(name).name != name or not name.endswith('.rgba'):
            raise ValueError('raw capture name must be a plain .rgba filename')
        path = self.paths.captures / name
        result = self.command('capture-raw', path)
        if (result.get('width'), result.get('height'), result.get('format')) != (
                160, 144, 'rgba32'):
            raise MgbaServiceError('mGBA returned an unexpected raw framebuffer format')
        expected_size = 160 * 144 * 4
        if not path.is_file() or path.stat().st_size != expected_size:
            raise MgbaServiceError(
                f'mGBA raw framebuffer is not {expected_size} bytes: {path}'
            )
        return path

    def save_state(self, path: Path, scenario_id: str) -> None:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.command('save', path)
        metadata = {
            'schema': 'gbre.mgba-state.v1',
            'rom_sha1': self.expected_sha1,
            'mgba_commit': MGBA_COMMIT,
            'scenario_id': scenario_id,
        }
        path.with_suffix(path.suffix + '.gbre.json').write_text(
            json.dumps(metadata, indent=2) + '\n'
        )

    def load_state(self, path: Path, scenario_id: str) -> None:
        path = path.resolve()
        metadata_path = path.with_suffix(path.suffix + '.gbre.json')
        if not path.is_file() or not metadata_path.is_file():
            raise MgbaServiceError(f'save state or metadata is missing: {path}')
        metadata = json.loads(metadata_path.read_text())
        expected = {
            'schema': 'gbre.mgba-state.v1',
            'rom_sha1': self.expected_sha1,
            'mgba_commit': MGBA_COMMIT,
            'scenario_id': scenario_id,
        }
        if metadata != expected:
            raise MgbaServiceError(
                f'save-state metadata is incompatible: {metadata_path}'
            )
        self.command('load', path)

    def advance_to_landmark(self, condition: str, timeout: int) -> dict[str, Any]:
        for _ in range(timeout + 1):
            observation = self.observe()
            if condition_matches(condition, observation):
                return observation
            self.step()
        raise MgbaServiceError(
            f'landmark {condition!r} was not reached within {timeout} frames'
        )

    def stop(self, *, force: bool = False) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None and not force and self.socket is not None:
            try:
                self.command('shutdown')
            except (MgbaServiceError, OSError):
                force = True
        if process.poll() is None:
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
        if self.reader is not None:
            self.reader.close()
        if self.socket is not None:
            self.socket.close()
        if self.log_file is not None:
            self.log_file.close()
        self.reader = None
        self.socket = None
        self.process = None
        self.log_file = None

    def __enter__(self) -> MgbaService:
        self.start()
        return self

    def __exit__(self, _kind, _value, _traceback) -> None:
        self.stop()
