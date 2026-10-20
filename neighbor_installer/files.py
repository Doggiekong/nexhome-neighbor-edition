"""Bounded regular-file operations and durable local journals."""

import contextlib
import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path


class InstallerError(Exception):
    """Only a stable, non-sensitive error code may leave the engine."""


def inventory(directory):
    directory = Path(directory)
    if directory.is_symlink():
        raise InstallerError("SYMLINK_REFUSED")
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise InstallerError("NOT_DIRECTORY")
    result = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise InstallerError("SYMLINK_REFUSED")
        if path.is_dir():
            continue
        if not path.is_file():
            raise InstallerError("NON_REGULAR_FILE")
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        total += path.stat().st_size
        if total > 32 * 1024 * 1024 or len(result) >= 1024:
            raise InstallerError("TREE_TOO_LARGE")
        result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path, default=None):
    if path.is_symlink():
        raise InstallerError("SYMLINK_REFUSED")
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, RecursionError):
        raise InstallerError("LOCAL_METADATA_INVALID") from None


def durable(path, data):
    path = Path(path)
    if path.is_symlink():
        raise InstallerError("SYMLINK_REFUSED")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + ".tmp")
    if temp.is_symlink():
        raise InstallerError("SYMLINK_REFUSED")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def guarded_root(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise InstallerError("CONFIG_ROOT_INVALID")
    for relative in ("custom_components", ".storage", ".nexhome-installer"):
        path = root / relative
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise InstallerError("CONFIG_CHILD_INVALID")
    return root.resolve()


@contextlib.contextmanager
def lock(root):
    state = guarded_root(root) / ".nexhome-installer"
    state.mkdir(mode=0o700, exist_ok=True)
    os.chmod(state, 0o700)
    fd = os.open(state / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InstallerError("BUSY") from None
        yield state
    finally:
        os.close(fd)


def copy_tree(source, destination, private=False):
    files = inventory(source)
    destination.mkdir(parents=True, mode=0o700 if private else 0o755, exist_ok=False)
    for relative in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
        shutil.copy2(source / relative, target)
        with target.open('rb') as stream:
            os.fsync(stream.fileno())
        if private:
            os.chmod(target, 0o600)
    if inventory(destination) != files:
        raise InstallerError("COPY_HASH_MISMATCH")


def remove_owned(path, parent):
    path = Path(path)
    if path.parent.resolve() != Path(parent).resolve() or path.is_symlink():
        raise InstallerError("DELETE_BOUNDARY")
    inventory(path)
    if path.exists():
        shutil.rmtree(path)
