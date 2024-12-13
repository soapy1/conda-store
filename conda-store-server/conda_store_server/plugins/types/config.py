# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


class ConfigPlugin:
    """
    Interface for Config plugins. These plugins

      * :meth: `validate`
      * :meth: `load'
    """

    def load(self, config_file: str):
        """
        Loads config from a file
        """
        raise NotImplementedError
    
    def validate(self, conda_store) -> bool:
        """
        Validate the specified config

        :param conda_store: a conda_store:CondaStore instance
        """
        raise NotImplementedError
