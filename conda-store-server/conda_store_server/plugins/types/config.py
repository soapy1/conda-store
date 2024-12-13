# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


class ConfigPlugin:
    """
    Interface for Config plugins. These plugins

      * :meth: `validate`
      * :meth: `load_config_file'
    """

    def load_config_file(self, config_file: str):
        """
        Loads config from a file
        """
        raise NotImplementedError
    
    def validate(self, conda_store):
        """
        Validate the specified config. Raise an error if the config
        is not valid

        :param conda_store: a conda_store:CondaStore instance
        """
        raise NotImplementedError
