# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import typing
import pluggy

from conda_store_server.exception import CondaStorePluginNotFoundError
from conda_store_server.plugins import BUILTIN_PLUGINS
from conda_store_server.plugins.types import types


class PluginManager(pluggy.PluginManager):
    """
    PluginManager extends pluggy's plugin manager in order to extend
    functionality for
      * retrieving CondaStore type plugins (eg. TypeLockPlugin),
      * discovering and registering CondaStore plugins
    """

    def _get_plugins(self, hook_fn: typing.Callable):
        """Returns a dict of plugin name to class, given the hook function
        to run to get the plugin iterator
        """
        plugins = [item for items in hook_fn() for item in items]
        return {p.name.lower(): p for p in plugins}

    def _get_plugin(self, get_plugins_fn: typing.Callable, name: str):
        """Returns a plugin of a given type and name"""
        plugins = get_plugins_fn()

        if name not in plugins:
            raise CondaStorePluginNotFoundError(
                plugin=name, available_plugins=plugins.keys()
            )

        return plugins[name]

    def get_trait_config_plugins(self) -> dict[str, types.TypeTraitConfigPlugin]:
        """Returns a dict of config plugin name to class"""
        return self._get_plugins(self.hook.trait_config_plugins)

    def get_lock_plugins(self) -> dict[str, types.TypeLockPlugin]:
        """Returns a dict of lock plugin name to class"""
        return self._get_plugins(self.hook.lock_plugins)

    def get_lock_plugin(self, name: str) -> types.TypeLockPlugin:
        """Returns a lock plugin by name"""
        return self._get_plugin(self.get_lock_plugins, name)

    def get_storage_plugins(self) -> dict[str, types.TypeStoragePlugin]:
        """Returns a dict of storage plugin name to class"""
        return self._get_plugins(self.hook.storage_plugins)

    def get_storage_plugin(self, name: str) -> types.TypeStoragePlugin:
        """Returns a storage plugin by name"""
        return self._get_plugin(self.get_storage_plugins, name)

    def collect_plugins(self) -> None:
        """Registers all availble plugins"""
        # TODO: support loading user defined plugins (eg. https://github.com/conda/conda/blob/cf3a0fa9ce01ada7a4a0c934e17be44b94d4eb91/conda/plugins/manager.py#L131)
        for plugin in BUILTIN_PLUGINS:
            self.register(plugin)
