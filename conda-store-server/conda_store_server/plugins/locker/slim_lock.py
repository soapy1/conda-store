# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import json
import os
import pathlib
import typing

import yaml
from conda_lock.conda_lock import run_lock

from conda_store_server._internal import conda_utils, schema
from conda_store_server.plugins import hookspec
from conda_store_server.plugins.plugin_context import PluginContext

class SlimLock():
    @classmethod
    def name():
        "slim-lock"

    def __init__(self, *args, **kwargs):
        # TODO: config plugin
        self.conda_command = kwargs.get("conda_command") or "mamba"
        self.conda_flags = kwargs.get("conda_flags") or "--strict-channel-priority"
    
    @hookspec.hookimpl
    def lock_environment(
        self,
        context: PluginContext,
        spec: schema.CondaSpecification, 
        platforms: typing.List[str] = [conda_utils.conda_platform()],
    ) -> PluginContext:
        context.log.info("lock_environment entrypoint for slim-lock")

        environment_filename = pathlib.Path.cwd() / "environment.yaml"
        lockfile_filename = pathlib.Path.cwd() / "conda-lock.yaml"

        with environment_filename.open("w") as f:
            json.dump(spec.dict(), f)

        context.log.info(
            "Note that the output of `conda config --show` displayed below only reflects "
            "settings in the conda configuration file, which might be overridden by "
            "variables required to be set by conda-store via the environment. Overridden "
            f"settings: CONDA_FLAGS={self.conda_flags}"
        )

        # The info command can be used with either mamba or conda
        context.run_command([self.conda_command, "info"])
        # The config command is not supported by mamba
        context.run_command(["conda", "config", "--show"])
        context.run_command(["conda", "config", "--show-sources"])

        # conda-lock ignores variables defined in the specification, so this code
        # gets the value of CONDA_OVERRIDE_CUDA and passes it to conda-lock via
        # the with_cuda parameter, see:
        # https://github.com/conda-incubator/conda-store/issues/719
        # https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-virtual.html#overriding-detected-packages
        # TODO: Support all variables once upstream fixes are made to conda-lock,
        # see the discussion in issue 719.
        if spec.variables is not None:
            cuda_version = spec.variables.get("CONDA_OVERRIDE_CUDA")
        else:
            cuda_version = None

        # CONDA_FLAGS is used by conda-lock in conda_solver.solve_specs_for_arch
        try:
            conda_flags_name = "CONDA_FLAGS"
            print(f"{conda_flags_name}={self.conda_flags}")
            os.environ[conda_flags_name] = self.conda_flags

            run_lock(
                environment_files=[environment_filename],
                platforms=platforms,
                lockfile_path=lockfile_filename,
                conda_exe=self.conda_command,
                with_cuda=cuda_version,
            )
        finally:
            os.environ.pop(conda_flags_name, None)

        with lockfile_filename.open() as f:
            return yaml.safe_load(f)
