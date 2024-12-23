# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from traitlets import (
    Bool,
    Dict,
    List,
    Type,
    Unicode,
)
from minio.credentials.providers import Provider

from conda_store_server.plugins.hookspec import hookimpl
from conda_store_server.plugins.types import trait_config, types

from . import PLUGIN_NAME


class S3Storage(trait_config.TraitConfigPlugin):
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


@hookimpl
def trait_config_plugins():
    """conda-store s3 storage config plugin"""
    yield types.TypeTraitConfigPlugin(
        name=PLUGIN_NAME,
        synopsis="Config for the S3 storage plugin",
        backend=S3Storage,
    )
