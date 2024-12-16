# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from traitlets.config import LoggingConfigurable


class TraitConfigPlugin(LoggingConfigurable):
    """
    Interface for Config plugin using traitlets. 
    """
