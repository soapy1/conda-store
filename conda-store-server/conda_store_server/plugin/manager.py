# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server.plugin.v1.lock import LockPlugin


class Manager():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Manager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # plugins are registered in the map of the form
        # {plugin_name: plugin_class}
        self.registered = {}

    def get_lock_plugins(self):
        """Returns a dict of all registered lock plugins, keyed by the plugin name"""
        return {name: plugin for name, plugin in self.registered.items() if issubclass(plugin, LockPlugin)}
    
    def register_plugin(self, p):
        """Adds plugin to the list of registered plugins"""
        plugin_name = p.name()
        if plugin_name not in self.registered:
            self.registered[plugin_name] = p

