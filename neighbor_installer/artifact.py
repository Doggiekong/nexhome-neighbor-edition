"""Pinned manifest trust boundary; no implicit downloads or execution."""

import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from packaging.version import InvalidVersion, Version

from .files import InstallerError, inventory, load
from .product import FIELDS, validate_identity


@dataclass(frozen=True)
class Artifact:
    directory: Path
    metadata: dict
    manifest_sha256: str

    @classmethod
    def open(cls, directory, expected_sha256):
        directory = Path(directory)
        if directory.is_symlink() or (directory / "artifact.json").is_symlink():
            raise InstallerError("ARTIFACT_SYMLINK")
        manifest = directory / "artifact.json"
        if not manifest.is_file() or manifest.stat().st_size > 1024 * 1024:
            raise InstallerError("ARTIFACT_MANIFEST_INVALID")
        actual = hashlib.sha256(manifest.read_bytes()).hexdigest()
        if not expected_sha256 or actual != expected_sha256:
            raise InstallerError("ARTIFACT_PIN_MISMATCH")
        metadata = load(manifest)
        if not isinstance(metadata, dict):
            raise InstallerError('ARTIFACT_METADATA_INVALID')
        extra = set(FIELDS) if metadata.get('schema') == 2 else set()
        if set(metadata) != extra | {
            'schema', 'version', 'revision', 'origin', 'tested_ha_versions', 'files'
        }:
            raise InstallerError('ARTIFACT_METADATA_INVALID')
        if metadata.get("schema") not in (1, 2) or not all(
            isinstance(metadata.get(key), str) and 0 < len(metadata[key]) <= 256
            for key in ("version", "revision", "origin")
        ):
            raise InstallerError("ARTIFACT_METADATA_INVALID")
        try:
            Version(metadata["version"])
        except InvalidVersion:
            raise InstallerError("ARTIFACT_VERSION_INVALID") from None
        expected = metadata.get("files")
        if metadata['origin'] != 'https://github.com/Doggiekong/nexhome-neighbor-edition' and not re.fullmatch(
            r'urn:nexhome:fixture:[a-z0-9-]+', metadata['origin']
        ):
            raise InstallerError('ARTIFACT_ORIGIN_UNTRUSTED')
        if not re.fullmatch(r'[a-f0-9]{40}', metadata['revision']):
            raise InstallerError('ARTIFACT_REVISION_INVALID')
        versions = metadata.get('tested_ha_versions')
        if not isinstance(versions, list) or not versions or not all(isinstance(v, str) for v in versions):
            raise InstallerError('ARTIFACT_HA_MATRIX_REQUIRED')
        if not isinstance(expected, dict) or not expected:
            raise InstallerError("ARTIFACT_FILES_INVALID")
        for name in expected:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
                raise InstallerError("ARTIFACT_PATH_INVALID")
        files = inventory(directory / "nexhome")
        if files != expected:
            raise InstallerError("ARTIFACT_FILES_MISMATCH")
        manifest_data = load(directory / "nexhome/manifest.json")
        if manifest_data.get("domain") != "nexhome" or manifest_data.get("version") != metadata["version"]:
            raise InstallerError("ARTIFACT_INTEGRATION_INVALID")
        if metadata['schema'] == 2:
            info = validate_identity({k: metadata[k] for k in FIELDS}, metadata['version'])
            if load(directory / 'nexhome/product.json') != info:
                raise InstallerError('ARTIFACT_PRODUCT_MISMATCH')
        if metadata['schema'] == 1 and 'product.json' in files:
            raise InstallerError('ARTIFACT_PRODUCT_SCHEMA_REQUIRED')
        for name in files:
            if name.endswith(".py"):
                try:
                    ast.parse((directory / "nexhome" / name).read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeError, RecursionError):
                    raise InstallerError("ARTIFACT_SYNTAX_INVALID") from None
        return cls(directory, metadata, actual)

    def revalidate(self):
        return self.open(self.directory, self.manifest_sha256)
