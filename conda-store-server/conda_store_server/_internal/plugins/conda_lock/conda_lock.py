# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import json
import os
import tempfile
import pathlib

import yaml

from conda_lock.conda_lock import run_lock

from conda_store_server.plugin.v1.lock import LockPlugin
from conda_store_server._internal.action.utils import logged_command


class CondaLock(LockPlugin):
    @classmethod
    def name(cls):
        return "conda-lock"
    
    def __init__(self, *args, **kwargs):
        # TODO: config plugin
        self.conda_command = kwargs.get("conda_command") or "mamba"
        self.conda_flags = kwargs.get("conda_flags") or "--strict-channel-priority"
        self.workdir = str(tempfile.TemporaryDirectory())
        return super().__init__(*args, **kwargs)

    def synopsis(self):
        return "Use conda lock to build lock file"
    
    def lock_environment(self, spec, platforms, logger):
        logger.info("lock_environment entrypoint for conda_lock")
        workdir = pathlib.Path(self.workdir)
        workdir.mkdir(parents=True)
        environment_filename = workdir / "environment.yaml"
        lockfile_filename = workdir / "conda-lock.yaml"

        with environment_filename.open("w") as f:
            json.dump(spec.dict(), f)

        if spec.variables is not None:
            cuda_version = spec.variables.get("CONDA_OVERRIDE_CUDA")
        else:
            cuda_version = None

        # CONDA_FLAGS is used by conda-lock in conda_solver.solve_specs_for_arch
        try:
            conda_flags_name = "CONDA_FLAGS"
            print(f"{conda_flags_name}={self.conda_flags}")
            os.environ[conda_flags_name] = self.conda_flags

            logger.info("running lock")
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
    
    def to_environment_spec(self):
        return {}
    
    def from_environment_spec(self):
        return {}
    