# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import io
import logging
import minio

from conda_store_server import api
from conda_store_server._internal import orm

from conda_store_server.plugins.hookspec import hookimpl
from conda_store_server.plugins.types import storage, types

from . import PLUGIN_NAME


class S3Storage(storage.StoragePlugin):
    def __init__(self, conda_store):
        self.conda_store = conda_store
        self.log = logging.getLogger(__name__)

        # get config plugin
        config_plugin = conda_store.plugin_manager.get_trait_config_plugin(name=PLUGIN_NAME)
        self.config = config_plugin.backend(parent=conda_store.config, log=conda_store.log)

    @property
    def _credentials(self):
        if self.config.credentials is None:
            return None

        return self.config.credentials(*self.config.credentials_args, **self.config.credentials_kwargs)

    @property
    def internal_client(self):
        if hasattr(self, "_internal_client"):
            return self._internal_client

        self.log.debug(
            f"setting up internal client endpoint={self.config.internal_endpoint} region={self.config.region} secure={self.config.internal_secure}"
        )
        self._internal_client = minio.Minio(
            self.config.internal_endpoint,
            self.config.access_key,
            self.config.secret_key,
            region=self.config.region,
            secure=self.config.internal_secure,
            credentials=self._credentials,
        )
        self._check_bucket_exists()
        return self._internal_client

    @property
    def external_client(self):
        if hasattr(self, "_external_client"):
            return self._external_client

        self.log.debug(
            f"setting up external client endpoint={self.config.external_endpoint} region={self.config.region} secure={self.config.external_secure}"
        )
        self._external_client = minio.Minio(
            self.config.external_endpoint,
            self.config.access_key,
            self.config.secret_key,
            region=self.config.region,
            secure=self.config.external_secure,
            credentials=self._credentials,
        )
        return self._external_client

    def _check_bucket_exists(self):
        if not self._internal_client.bucket_exists(self.config.bucket_name):
            raise ValueError(f"S3 bucket={self.config.bucket_name} does not exist")

    def fset(self, db, build_id, key, filename, content_type, artifact_type):
        self.internal_client.fput_object(
            self.config.bucket_name, key, filename, content_type=content_type
        )

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
        
    def set(self, db, build_id, key, value, content_type, artifact_type):
        self.internal_client.put_object(
            self.config.bucket_name,
            key,
            io.BytesIO(value),
            length=len(value),
            content_type=content_type,
        )
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
        response = self.internal_client.get_object(self.config.bucket_name, key)
        return response.read()

    def get_url(self, key):
        return self.external_client.presigned_get_object(self.config.bucket_name, key)

    def delete(self, db, build_id, key):
        self.internal_client.remove_object(self.config.bucket_name, key)
        build_artifact = api.get_build_artifact(db, build_id, key)
        db.delete(build_artifact)
        db.commit()

@hookimpl
def storage_plugins():
    """conda-store s3 storage config plugin"""
    yield types.TypeStoragePlugin(
        name=PLUGIN_NAME,
        synopsis="Upload artifacts to s3",
        backend=S3Storage,
    )