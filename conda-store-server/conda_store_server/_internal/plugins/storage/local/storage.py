# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


import os
import posixpath
import shutil
import logging

from conda_store_server import api
from conda_store_server._internal import orm

from conda_store_server.plugins.hookspec import hookimpl
from conda_store_server.plugins.types import storage, types

from . import PLUGIN_NAME


class LocalStorage(storage.StoragePlugin):
    def __init__(self, conda_store):
        self.conda_store = conda_store
        self.log = logging.getLogger(__name__)

        # get config plugin
        config_plugin = conda_store.plugin_manager.get_trait_config_plugin(name=PLUGIN_NAME)
        self.config = config_plugin.backend(parent=conda_store.config, log=conda_store.log)

    def fset(self, db, build_id, key, filename, content_type=None, artifact_type=None):
        destination_filename = os.path.abspath(os.path.join(self.config.storage_path, key))
        os.makedirs(os.path.dirname(destination_filename), exist_ok=True)

        shutil.copyfile(filename, destination_filename)
        ba = orm.BuildArtifact
        exists = (
            db.query(ba)
            .filter(ba.build_id == build_id)
            .filter(ba.key == key)
            .filter(ba.artifact_type == artifact_type)
            .first()
        )
        if not exists:
            db.add(ba(build_id=build_id, key=key, artifact_type=artifact_type))
            db.commit()


    def set(self, db, build_id, key, value, content_type=None, artifact_type=None):
        destination_filename = os.path.join(self.config.storage_path, key)
        os.makedirs(os.path.dirname(destination_filename), exist_ok=True)

        with open(destination_filename, "wb") as f:
            f.write(value)
        ba = orm.BuildArtifact
        exists = (
            db.query(ba)
            .filter(ba.build_id == build_id)
            .filter(ba.key == key)
            .filter(ba.artifact_type == artifact_type)
            .first()
        )
        if not exists:
            db.add(ba(build_id=build_id, key=key, artifact_type=artifact_type))
            db.commit()

    def get(self, key):
        with open(os.path.join(self.config.storage_path, key), "rb") as f:
            return f.read()

    def get_url(self, key):
        return posixpath.join(self.config.storage_url, key)

    def delete(self, db, build_id, key):
        filename = os.path.join(self.config.storage_path, key)
        try:
            os.remove(filename)
        except FileNotFoundError:
            # The DB can contain multiple entries pointing to the same key, like
            # a log file. This skips files that were previously processed and
            # deleted. See LocalStorage.fset and Storage.fset, which are used
            # for saving build artifacts
            pass
        build_artifact = api.get_build_artifact(db, build_id, key)
        db.delete(build_artifact)
        db.commit()


@hookimpl
def storage_plugins():
    """conda-store local storage config plugin"""
    yield types.TypeStoragePlugin(
        name=PLUGIN_NAME,
        synopsis="Save artifacts to local storage",
        backend=LocalStorage,
    )
