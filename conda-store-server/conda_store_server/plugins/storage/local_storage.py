# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import io
import os
import posixpath
import shutil

import minio
from minio.credentials.providers import Provider
from traitlets import Bool, Dict, List, Type, Unicode
from traitlets.config import LoggingConfigurable

from conda_store_server import CONDA_STORE_DIR, api
from conda_store_server._internal import orm, schema

from conda_store_server.plugins import hookspec


class LocalStorage(LoggingConfigurable):
    storage_path = Unicode(
        str(CONDA_STORE_DIR / "storage"),
        help="directory to store binary blobs of conda-store artifacts",
        config=True,
    )

    storage_url = Unicode(
        help="unauthenticated url where artifacts in storage path are being served from",
        config=True,
    )

    @hookspec.hookimpl
    def storage_fset(
        self,
        db,
        build_id: int,
        key: str,
        filename: str,
        artifact_type: schema.BuildArtifactType,
    ):
        destination_filename = os.path.abspath(os.path.join(self.storage_path, key))
        os.makedirs(os.path.dirname(destination_filename), exist_ok=True)

        shutil.copyfile(filename, destination_filename)

    @hookspec.hookimpl
    def storage_set(
        self,
        db,
        build_id: int,
        key: str,
        value: bytes,
        artifact_type: schema.BuildArtifactType,
    ):
        destination_filename = os.path.join(self.storage_path, key)
        os.makedirs(os.path.dirname(destination_filename), exist_ok=True)

        with open(destination_filename, "wb") as f:
            f.write(value)

    @hookspec.hookimpl
    def storage_get(self, key):
        with open(os.path.join(self.storage_path, key), "rb") as f:
            return f.read()

    @hookspec.hookimpl
    def storage_get_url(self, key):
        return posixpath.join(self.storage_url, key)

    @hookspec.hookimpl
    def storage_delete(self, db, build_id: int, key: str):
        filename = os.path.join(self.storage_path, key)
        try:
            os.remove(filename)
        except FileNotFoundError:
            # The DB can contain multiple entries pointing to the same key, like
            # a log file. This skips files that were previously processed and
            # deleted. See LocalStorage.fset and Storage.fset, which are used
            # for saving build artifacts
            pass
