# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from traitlets.config import LoggingConfigurable

from conda_store_server import api
from conda_store_server._internal import orm, schema
from conda_store_server.plugins import hookspec


class BaseStorage(LoggingConfigurable):
    @hookspec.hookimpl
    def storage_fset(
        self,
        db,
        build_id: int,
        key: str,
        filename: str,
        artifact_type: schema.BuildArtifactType,
    ):
        ba = orm.BuildArtifact
        exists = (
            db.query(ba)
            .filter(ba.build_id == build_id)
            .filter(ba.key == key)
            .filter(ba.artifact_type == artifact_type)
            .first()
        )
        if not exists:
            db.add(ba(build_id=build_id, key=key, artifact_type=artifact_type))
            db.commit()

    @hookspec.hookimpl
    def storage_set(
        self,
        db,
        build_id: int,
        key: str,
        value: bytes,
        artifact_type: schema.BuildArtifactType,
    ):
        ba = orm.BuildArtifact
        exists = (
            db.query(ba)
            .filter(ba.build_id == build_id)
            .filter(ba.key == key)
            .filter(ba.artifact_type == artifact_type)
            .first()
        )
        if not exists:
            db.add(ba(build_id=build_id, key=key, artifact_type=artifact_type))
            db.commit()

    @hookspec.hookimpl
    def storage_delete(self, db, build_id: int, key: str):
        build_artifact = api.get_build_artifact(db, build_id, key)
        db.delete(build_artifact)
        db.commit()
