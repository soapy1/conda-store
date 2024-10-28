# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server.plugin.v1.lock import LockPlugin


class Manager():
    def __init__(self):
        self.registered = []

    def get_lock_plugins(self):
        """Returns a list of all registered lock plugins"""
        return [p for p in self.registered if isinstance(p, LockPlugin)]
    
    def register_plugin(self, p):
        """Adds plugin to the list of registered plugins"""
        if p not in self.registered:
            self.registered.append(p)


