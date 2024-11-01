# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pluggy
import typing

from conda_store_server._internal import conda_utils, schema
from conda_store_server.plugins import plugin_context


spec_name = "conda-store-server"

hookspec = pluggy.HookspecMarker(spec_name)

hookimpl = pluggy.HookimplMarker(spec_name)


class CondaStoreSpecs:
    """Conda Store hookspecs"""

    @hookspec
    def lock_environment(
        self,
        context: plugin_context.PluginContext,
        spec: schema.CondaSpecification, 
        platforms: typing.List[str] = [conda_utils.conda_platform()],
    ) -> str:
        """Lock spec"""

    @hookspec
    def storage_fset(
        self,
        db,
        build_id: int,
        key: str,
        filename: str,
        content_type: str,
        artifact_type: schema.BuildArtifactType,
    ) -> str:
        """Upload file to storage"""

    @hookspec
    def storage_set(
        self,
        db,
        build_id: int,
        key: str,
        value: bytes,
        content_type: str,
        artifact_type: schema.BuildArtifactType,
    ) -> str:
        """Upload blob to storage"""

    @hookspec(firstresult=True)
    def storage_get(
        self,
        key: str,
    ) -> str:
        """Get an artifact from storage"""
    
    @hookspec(firstresult=True)
    def storage_get_url(
        self,
        key: str,
    ) -> str:
        """Get an artifact url from storage"""

    @hookspec
    def delete(
        self,
        db, 
        build_id: int, 
        key: str
    ) -> str:
        """Delete an artifact from storage"""
