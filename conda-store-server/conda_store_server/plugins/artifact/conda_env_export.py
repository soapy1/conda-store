# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import json
import yaml

from sqlalchemy.orm import Session

from conda_store_server._internal import schema, orm
from conda_store_server.plugins import hookspec
from conda_store_server.plugins.plugin_context import PluginContext


class CondaEnvExport():
    @classmethod
    def name(cls):
        return "artifact-conda-env-export"
    
    def __init__(self, conda_command="mamba", *kwargs):
        self.conda_command = conda_command
    
    @hookspec.hookimpl
    def artifact_build(
        self,
        context: PluginContext,
        db: Session,
        build: orm.Build
    ):
        context.log.info("building artifact with artifact-conda-env-export")
        conda_prefix = build.build_path(context.conda_store)

        command = [
            self.conda_command,
            "env",
            "export",
            "--prefix",
            str(conda_prefix),
            "--json",
        ]

        result = context.run(command, check=True, redirect_stderr=False)
        if result.stderr:
            context.log.warning(f"conda env export stderr: {result.stderr}")
        result_json = json.loads(result.stdout)

        conda_prefix_export = yaml.dump(result_json).encode("utf-8")

        context.conda_store.plugin_manager.hook.storage_set(
            db=db,
            build_id=build.id,
            key=build.conda_env_export_key,
            value=conda_prefix_export,
            content_type="text/yaml",
            artifact_type=schema.BuildArtifactType.YAML,
        )
        
