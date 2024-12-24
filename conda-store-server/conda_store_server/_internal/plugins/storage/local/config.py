# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from traitlets import Unicode

from conda_store_server.plugins.hookspec import hookimpl
from conda_store_server.plugins.types import trait_config, types
from conda_store_server import CONDA_STORE_DIR

from . import PLUGIN_NAME


class LocalStorage(trait_config.TraitConfigPlugin):
    storage_path = Unicode(
        str(CONDA_STORE_DIR / "storage"),
        help="directory to store binary blobs of conda-store artifacts",
        config=True,
    )

    storage_url = Unicode(
        help="unauthenticated url where artifacts in storage path are being served from",
        config=True,
    )


@hookimpl
def trait_config_plugins():
    """conda-store local storage config plugin"""
    yield types.TypeTraitConfigPlugin(
        name=PLUGIN_NAME,
        synopsis="Config for the local storage plugin",
        backend=LocalStorage,
    )
