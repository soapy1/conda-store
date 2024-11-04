# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import functools
import typing

from conda_store_server.exception import CondaStorePluginNotFoundError


def build_task(fn: typing.Callable):
    @functools.wraps(fn)
    def wrapper(*args, conda_store, db, namespace=None, environment=None, **kwargs):
        build_context = BuildContext(db, conda_store, namespace, environment)
        # TODO: register all appropriate plugins
        build_context.register_lock_plugin()
        
        fn(build_context, *args, **kwargs)

        # TODO: clean up all plugins that were registered
        build_context.unregister_lock_plugin()

    return wrapper


class BuildContext():
    def __init__(self, db, conda_store, namespace=None, environment_name=None):
        self.db = db
        self.conda_store = conda_store
        self.namespace = namespace
        self.environment_name = environment_name
        self.settings = conda_store.get_settings(
            db=db,
            namespace=namespace,
            environment_name=environment_name,
        )

    def register_lock_plugin(self):
        locker_plugin_name = self.conda_store.locker_plugin_name
        locker_plugin = self.conda_store.plugin_registry.get_plugin(locker_plugin_name)   
        if locker_plugin is None:
            raise CondaStorePluginNotFoundError(self.conda_store.locker_plugin_name, self.conda_store.plugin_registry.list_plugin_names())     
        self.conda_store.plugin_manager.register(
            locker_plugin(
                conda_command=self.settings.conda_command,
                conda_flags=self.conda_store.conda_flags),
            name=locker_plugin_name
        )

    def unregister_lock_plugin(self):
        self.conda_store.plugin_manager.unregister(
            name=self.conda_store.locker_plugin_name
        )
