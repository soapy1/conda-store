# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server.plugins.lock import conda_lock
from conda_store_server.plugins.lock import slim_lock

from conda_store_server.plugins.storage import base_storage
from conda_store_server.plugins.storage import local_storage
from conda_store_server.plugins.storage import s3_storage


BUILTIN_PLUGINS = [
    conda_lock.CondaLock,
    slim_lock.SlimLock,
    base_storage.BaseStorage,
    local_storage.LocalStorage,
    s3_storage.S3Storage,
]