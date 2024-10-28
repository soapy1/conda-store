# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

class LockPlugin():
    def initialize(self, *args, **kwargs):
        pass

    def synopsis(self):
        return ""
    
    def lock_environment(self, spec, platforms):
        """Solve the environment and generate a lockfile for a given spec on given platforms"""
        pass

    def to_environment_spec(self):
        """Converts the plugin's notion of an environment spec to a conda-store lock spec"""
        pass

    def from_environment_spec(self):
        """Converts a conda-store lock speck to the plugin's notion of a lock spec"""
        pass
