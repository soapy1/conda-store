# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from collections.abc import Iterable

import pluggy

from conda_store_server.plugins.types.lock import LockPlugin
from conda_store_server.plugins.types.trait_config import TraitConfigPlugin
from conda_store_server.plugins.types.storage import StoragePlugin

spec_name = "conda-store"
hookspec = pluggy.HookspecMarker(spec_name)
hookimpl = pluggy.HookimplMarker(spec_name)


class CondaStoreSpecs:
    """Conda Store hookspecs"""

    @hookspec
    def lock_plugins(self) -> Iterable[LockPlugin]:
        """Lock spec"""
        yield from ()

    @hookspec
    def storage_plugins(self) -> Iterable[StoragePlugin]:
        """Storage spec"""
        yield from ()

    @hookspec
    def trait_config_plugins(self) -> Iterable[TraitConfigPlugin]:
        """Config spec"""
        yield from ()
