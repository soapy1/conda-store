# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server._internal.plugins.lock.conda_lock import conda_lock
from conda_store_server._internal.plugins.config.conda_store import conda_store

from conda_store_server._internal.plugins.storage.s3 import config as s3_config
from conda_store_server._internal.plugins.storage.s3 import storage as s3_storage


BUILTIN_PLUGINS = [
    conda_lock,
    conda_store,
    s3_config,
    s3_storage,
]
