# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server._internal import schema
from conda_store_server.plugins.plugin_context import PluginContext


class StoragePlugin:
    """
    Interface for the storage plugin. This plugin is responsible pushing artifacts
    to the storage backend
    """

    def fset(
        self,
        context: PluginContext,
        build_id: int,
        key: str,
        filename: str,
        artifact_type: schema.BuildArtifactType,
    ):
        """Upload a file given the path to a file

        Parameters
        ----------
        context : plugin_context.PluginContext
            plugin context to execute in
        build_id : int
            id of the build to associate the artifact with
        key : str
            name of the artifact
        filename : str
            full path of the file to upload
        artifact_type : schema.BuildArtifactType
            type of artifact that is being uploaded
        """
        raise NotImplementedError
    
    def set(
        self,
        context: PluginContext,
        build_id: int,
        key: str,
        value: str,
        artifact_type: schema.BuildArtifactType,
    ):
        """Upload content to the storage backend 

        Parameters
        ----------
        context : plugin_context.PluginContext
            plugin context to execute in
        build_id : int
            id of the build to associate the artifact with
        key : str
            name of the artifact
        value : str
            content to upload
        artifact_type : schema.BuildArtifactType
            type of artifact that is being uploaded
        """
        raise NotImplementedError
    
    def get(
        self,
        context: PluginContext,
        key: str,
    ) -> str:
        """Retrieve an artifact by a given key

        Parameters
        ----------
        context : plugin_context.PluginContext
            plugin context to execute in
        key : str
            name of the artifact

        Returns
        -------
        Content
            read the content of the artifact
        """
        raise NotImplementedError
    
    def get_url(
        self,
        context: PluginContext,
        key: str,
    ) -> str:
        """Retrieve the url to an artifact by a given key

        Parameters
        ----------
        context : plugin_context.PluginContext
            plugin context to execute in
        key : str
            name of the artifact

        Returns
        -------
        url
            the url
        """
        raise NotImplementedError
    
    def delete(
        self,
        context: PluginContext,
        build_id: int,
        key: str,
    ):
        """Delete an artifact by a given key

        Parameters
        ----------
        context : plugin_context.PluginContext
            plugin context to execute in
        build_id : int
            id of the build that the artifact is associated with
        key : str
            name of the artifact
        """
        raise NotImplementedError
