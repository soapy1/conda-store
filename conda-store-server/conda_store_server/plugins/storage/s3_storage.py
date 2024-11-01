# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import io

import minio
from minio.credentials.providers import Provider
from traitlets import Bool, Dict, List, Type, Unicode
from traitlets.config import LoggingConfigurable

from conda_store_server._internal import schema

from conda_store_server.plugins import hookspec


class S3Storage(LoggingConfigurable):
    internal_endpoint = Unicode(
        help="internal endpoint to reach s3 bucket e.g. 'minio:9000' this is the url that conda-store use for get/set s3 blobs",
        config=True,
    )

    external_endpoint = Unicode(
        help="external endpoint to reach s3 bucket e.g. 'localhost:9000' this is the url that users use for fetching s3 blobs",
        config=True,
    )

    access_key = Unicode(
        help="access key for S3 bucket",
        allow_none=True,
        config=True,
    )

    secret_key = Unicode(
        help="secret key for S3 bucket",
        allow_none=True,
        config=True,
    )

    region = Unicode(
        "us-east-1",
        help="region for s3 bucket",
        config=True,
    )

    bucket_name = Unicode(
        "conda-store",
        help="bucket name for s3 bucket",
        config=True,
    )

    internal_secure = Bool(
        True,
        help="use secure connection to connect to s3 bucket internally",
        config=True,
    )

    external_secure = Bool(
        True,
        help="use secure connection to collect to s3 bucket externally",
        config=True,
    )

    credentials = Type(
        klass=Provider,
        default_value=None,
        help="provider to use to get credentials for s3 access. see examples https://github.com/minio/minio-py/tree/master/examples and documentation https://github.com/minio/minio-py/blob/master/docs/API.md#1-constructor",
        allow_none=True,
        config=True,
    )

    credentials_args = List(
        [],
        help="arguments to pass to Provider",
        config=True,
    )

    credentials_kwargs = Dict(
        {},
        help="keyword arguments to pass to Provider",
        config=True,
    )

    @property
    def _credentials(self):
        if self.credentials is None:
            return None

        return self.credentials(*self.credentials_args, **self.credentials_kwargs)

    @property
    def internal_client(self):
        if hasattr(self, "_internal_client"):
            return self._internal_client

        self.log.debug(
            f"setting up internal client endpoint={self.internal_endpoint} region={self.region} secure={self.internal_secure}"
        )
        self._internal_client = minio.Minio(
            self.internal_endpoint,
            self.access_key,
            self.secret_key,
            region=self.region,
            secure=self.internal_secure,
            credentials=self._credentials,
        )
        self._check_bucket_exists()
        return self._internal_client

    @property
    def external_client(self):
        if hasattr(self, "_external_client"):
            return self._external_client

        self.log.debug(
            f"setting up external client endpoint={self.external_endpoint} region={self.region} secure={self.external_secure}"
        )
        self._external_client = minio.Minio(
            self.external_endpoint,
            self.access_key,
            self.secret_key,
            region=self.region,
            secure=self.external_secure,
            credentials=self._credentials,
        )
        return self._external_client

    def _check_bucket_exists(self):
        if not self._internal_client.bucket_exists(self.bucket_name):
            raise ValueError(f"S3 bucket={self.bucket_name} does not exist")


    @hookspec.hookimpl
    def storage_fset(
        self,
        db,
        build_id: int,
        key: str,
        filename: str,
        artifact_type: schema.BuildArtifactType,
    ):
        self.internal_client.fput_object(
            self.bucket_name, key, filename, content_type=content_type
        )

    @hookspec.hookimpl
    def storage_get(self, key):
        response = self.internal_client.get_object(self.bucket_name, key)
        return response.read()
        
    @hookspec.hookimpl
    def stroage_get_url(self, key):
        return self.external_client.presigned_get_object(self.bucket_name, key)

    @hookspec.hookimpl
    def storage_set(
        self,
        db,
        build_id: int,
        key: str,
        value: bytes,
        artifact_type: schema.BuildArtifactType,
    ):
        self.internal_client.put_object(
            self.bucket_name,
            key,
            io.BytesIO(value),
            length=len(value),
            content_type=content_type,
        )
        super().fset(db, build_id, key, value, artifact_type)

       
    @hookspec.hookimpl
    def storage_delete(self, db, build_id: int, key: str):
        self.internal_client.remove_object(self.bucket_name, key)
        super().delete(db, build_id, key)
