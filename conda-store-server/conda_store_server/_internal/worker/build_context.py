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
        build_context.register_build_time_plugins()
        fn(build_context, *args, **kwargs)
        build_context.unregister_build_time_plugins()

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

    def register_build_time_plugins(self):
        self.conda_store.load_plugin_by_name(
            self.conda_store.locker_plugin_name, 
            conda_command=self.settings.conda_command,
            conda_flags=self.conda_store.conda_flags
        )
       

    def unregister_build_time_plugins(self):
        self.conda_store.plugin_manager.unregister(
            name=self.conda_store.locker_plugin_name
        )
