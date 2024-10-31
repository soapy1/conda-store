# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pluggy
import typing

from conda_store_server._internal import conda_utils, schema
from conda_store_server.plugins import action_context


spec_name = "conda-store-server"

hookspec = pluggy.HookspecMarker(spec_name)

hookimpl = pluggy.HookimplMarker(spec_name)


class Locker:
    """Given specs, create a lockfile spec"""

    @hookspec
    def lock_environment(
        self,
        spec: schema.CondaSpecification, 
        platforms: typing.List[str] = [conda_utils.conda_platform()],
    ) -> action_context.ActionContext:
        """Lock spec"""
