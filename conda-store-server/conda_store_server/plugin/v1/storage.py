# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from conda_store_server._internal import schema

class StoragePlugin():
    def fset(
        self,
        db,
        build_id: int,
        key: str,
        filename: str,
        artifact_type: schema.BuildArtifactType,
    ):
        """Upsert a file to the storage backend"""
        raise NotImplementedError
    
    def set(
        self,
        db,
        build_id: int,
        key: str,
        value: bytes,
        artifact_type: schema.BuildArtifactType,
    ):
        """Upsert a file to the storage backend"""
        raise NotImplementedError
    
    def get(self, key: str):
        """Get an object by key"""
        raise NotImplementedError()

    def get_url(self, key: str) -> str:
        """Get a publicly availble url for an object by key"""
        raise NotImplementedError()

    def delete(self, db, build_id: int, key: str):
        """Delete an object by key"""
        raise NotImplementedError()