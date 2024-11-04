# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import collections
import datetime
import json
import pathlib
import re
import subprocess
import tempfile
import traceback
import typing

import yaml
from filelock import FileLock
from sqlalchemy.orm import Session

from conda_store_server import api
from conda_store_server._internal import action, conda_utils, orm, schema, utils
from conda_store_server.plugins.plugin_context import PluginContext
from conda_store_server._internal.worker import build_context


class LoggedStream:
    """Allows writing to storage via logging.StreamHandler"""

    def __init__(self, db, conda_store, build, prefix=None):
        self.db = db
        self.conda_store = conda_store
        self.build = build
        self.prefix = prefix

    def write(self, b, /):
        for line in b.split("\n"):
            # Skips empty lines
            if not line:
                continue
            if self.prefix is not None:
                line = self.prefix + line
            append_to_logs(self.db, self.conda_store, self.build, line + "\n")

    def flush(self):
        pass


def append_to_logs(db: Session, conda_store, build, logs: typing.Union[str, bytes]):
    # For instance, with local storage, this involves reading from and writing
    # to a file. Locking here prevents a race condition when multiple tasks
    # attempt to write to a shared resource, which is the log
    with FileLock(f"{build.build_path(conda_store)}.log.lock"):
        try:
            current_logs = conda_store.plugin_manager.hook.storage_get(key=build.log_key)
        except Exception:
            current_logs = b""

        if current_logs is None:
            current_logs = b""

        if isinstance(logs, str):
            logs = logs.encode("utf-8")
        elif logs is None:
            logs = b""

        conda_store.plugin_manager.hook.storage_set(
            db=db,
            build_id=build.id,
            key=build.log_key,
            value=current_logs + logs,
            content_type="text/plain",
            artifact_type=schema.BuildArtifactType.LOGS,
        )


def set_build_started(db: Session, build: orm.Build):
    build.status = schema.BuildStatus.BUILDING
    build.started_on = datetime.datetime.utcnow()
    db.commit()


def set_build_failed(
    db: Session, build: orm.Build, status_info: typing.Optional[str] = None
):
    build.status = schema.BuildStatus.FAILED
    build.status_info = status_info
    build.ended_on = datetime.datetime.utcnow()
    db.commit()


def set_build_canceled(
    db: Session, build: orm.Build, status_info: typing.Optional[str] = None
):
    build.status = schema.BuildStatus.CANCELED
    build.status_info = status_info
    build.ended_on = datetime.datetime.utcnow()
    db.commit()


def set_build_completed(db: Session, conda_store, build: orm.Build):
    build.status = schema.BuildStatus.COMPLETED
    build.ended_on = datetime.datetime.utcnow()

    directory_build_artifact = orm.BuildArtifact(
        build_id=build.id,
        artifact_type=schema.BuildArtifactType.DIRECTORY,
        key=str(build.build_path(conda_store)),
    )
    db.add(directory_build_artifact)

    build.environment.current_build = build
    build.environment.specification = build.specification
    db.commit()


def build_cleanup(
    db: Session,
    conda_store,
    build_ids: typing.List[str] = None,
    reason: str = None,
    is_canceled: bool = False,
):
    """Walk through all builds in BUILDING state and check that they are actively running

    Build can get stuck in the building state due to worker
    spontaineously dying due to memory errors, killing container, etc.
    """
    status = "CANCELED" if is_canceled else "FAILED"
    reason = (
        reason
        or f"""
Build marked as {status} on cleanup due to being stuck in BUILDING state
and not present on workers. This happens for several reasons: build is
canceled, a worker crash from out of memory errors, worker was killed,
or error in conda-store
"""
    )

    inspect = conda_store.celery_app.control.inspect()
    active_tasks = inspect.active()
    if active_tasks is None:
        conda_store.log.warning(
            "build cleanup failed: celery broker does not support inspect"
        )
        return

    build_active_tasks = collections.defaultdict(list)
    for worker_name, tasks in active_tasks.items():
        for task in tasks:
            match = re.fullmatch(r"build-(\d+)-(.*)", str(task["id"]))
            if match:
                build_id, name = match.groups()
                build_active_tasks[build_id].append(task["name"])

    if build_ids:
        builds = [api.get_build(db, build_id) for build_id in build_ids]
    else:
        builds = api.list_builds(db, status=schema.BuildStatus.BUILDING)

    for build in builds:
        if (
            build.status == schema.BuildStatus.BUILDING
            and str(build.id) not in build_active_tasks
            and (
                build.started_on
                < (datetime.datetime.utcnow() - datetime.timedelta(seconds=5))
            )
        ):
            conda_store.log.warning(
                f"marking build {build.id} as {status} since stuck in BUILDING state and not present on workers"
            )
            append_to_logs(
                db,
                conda_store,
                build,
                reason,
            )
            if is_canceled:
                set_build_canceled(db, build)
            else:
                set_build_failed(db, build)


@build_context.build_task
def build_conda_environment(build_context, build):
    """Build a conda environment with set uid/gid/and permissions and
    symlink the build to a named environment

    """
    try:
        set_build_started(build_context.db, build)
        # Note: even append_to_logs can fail due to filename size limit, so
        # check build_path length first
        conda_prefix = build.build_path(build_context.conda_store)
        append_to_logs(
            build_context.db,
            build_context.conda_store,
            build,
            f"starting build of conda environment {datetime.datetime.utcnow()} UTC\n",
        )

        conda_prefix.parent.mkdir(parents=True, exist_ok=True)

        environment_prefix = build.environment_path(build_context.conda_store)
        if environment_prefix is not None:
            environment_prefix.parent.mkdir(parents=True, exist_ok=True)

        is_lockfile = build.specification.is_lockfile

        with utils.timer(build_context.conda_store.log, f"building conda_prefix={conda_prefix}"):
            if is_lockfile:
                context = action.action_save_lockfile(
                    specification=schema.LockfileSpecification.parse_obj(
                        build.specification.spec
                    ),
                    stdout=LoggedStream(
                        db=build_context.db,
                        conda_store=build_context.conda_store,
                        build=build,
                        prefix="action_save_lockfile: ",
                    ),
                )
                result = context.result
            else:
                result = build_context.conda_store.plugin_manager.hook.lock_environment(
                    context=PluginContext(stdout=LoggedStream(
                        db=build_context.db,
                        conda_store=build_context.conda_store,
                        build=build,
                        prefix="hook-lock_environment: ",
                    )),
                    spec=schema.CondaSpecification.parse_obj(
                        build.specification.spec
                    ),
                    platforms=build_context.settings.conda_solve_platforms,
                )

            build_context.conda_store.plugin_manager.hook.storage_set(
                db=build_context.db,
                build_id=build.id,
                key=build.conda_lock_key,
                value=json.dumps(
                    result, indent=4, cls=utils.CustomJSONEncoder
                ).encode("utf-8"),
                content_type="application/json",
                artifact_type=schema.BuildArtifactType.LOCKFILE,
            )

            conda_lock_spec = result

            context = action.action_fetch_and_extract_conda_packages(
                conda_lock_spec=conda_lock_spec,
                pkgs_dir=conda_utils.conda_root_package_dir(),
                stdout=LoggedStream(
                    db=build_context.db,
                    conda_store=build_context.conda_store,
                    build=build,
                    prefix="action_fetch_and_extract_conda_packages: ",
                ),
            )

            context = action.action_install_lockfile(
                conda_lock_spec=conda_lock_spec,
                conda_prefix=conda_prefix,
                stdout=LoggedStream(
                    db=build_context.db,
                    conda_store=build_context.conda_store,
                    build=build,
                    prefix="action_install_lockfile: ",
                ),
            )

        if environment_prefix is not None:
            utils.symlink(conda_prefix, environment_prefix)

        action.action_set_conda_prefix_permissions(
            conda_prefix=conda_prefix,
            permissions=build_context.settings.default_permissions,
            uid=build_context.settings.default_uid,
            gid=build_context.settings.default_gid,
            stdout=LoggedStream(
                db=build_context.db,
                conda_store=build_context.conda_store,
                build=build,
                prefix="action_set_conda_prefix_permissions: ",
            ),
        )

        action.action_add_conda_prefix_packages(
            db=build_context.db,
            conda_prefix=conda_prefix,
            build_id=build.id,
            stdout=LoggedStream(
                db=build_context.db,
                conda_store=build_context.conda_store,
                build=build,
                prefix="action_add_conda_prefix_packages: ",
            ),
        )

        context = action.action_get_conda_prefix_stats(
            conda_prefix,
            stdout=LoggedStream(
                db=build_context.db,
                conda_store=build_context.conda_store,
                build=build,
                prefix="action_get_conda_prefix_stats: ",
            ),
        )
        build.size = context.result["disk_usage"]

        set_build_completed(build_context.db, build_context.conda_store, build)
    # Always mark build as failed first since other functions may throw an
    # exception
    except subprocess.CalledProcessError as e:
        set_build_failed(build_context.db, build)
        build_context.conda_store.log.exception(e)
        append_to_logs(build_context.db, build_context.conda_store, build, e.output)
        raise e
    except utils.BuildPathError as e:
        # Provide status_info, which will be exposed to the user, ONLY in this
        # case because the error message doesn't expose sensitive information
        set_build_failed(build_context.db, build, status_info=e.message)
        build_context.conda_store.log.exception(e)
        append_to_logs(build_context.db, build_context.conda_store, build, traceback.format_exc())
        raise e
    except Exception as e:
        set_build_failed(build_context.db, build)
        build_context.conda_store.log.exception(e)
        append_to_logs(build_context.db, build_context.conda_store, build, traceback.format_exc())
        raise e


@build_context.build_task
def solve_conda_environment(build_context, solve: orm.Solve):
    solve.started_on = datetime.datetime.utcnow()
    build_context.db.commit()

    conda_lock_spec = build_context.conda_store.plugin_manager.hook.lock_environment(
            context=PluginContext(),
            spec=schema.CondaSpecification.parse_obj(solve.specification.spec),
            platforms=[conda_utils.conda_platform()],
        )

    action.action_add_lockfile_packages(
        db=build_context.db,
        conda_lock_spec=conda_lock_spec,
        solve_id=solve.id,
    )

    solve.ended_on = datetime.datetime.utcnow()
    build_context.db.commit()


# TODO: replace with artifact plugin
@build_context.build_task
def build_conda_env_export(build_context, build: orm.Build):
    conda_prefix = build.build_path(build_context.conda_store)

    context = action.action_generate_conda_export(
        conda_command=build_context.settings.conda_command,
        conda_prefix=conda_prefix,
        stdout=LoggedStream(
            db=build_context.db,
            conda_store=build_context.conda_store,
            build=build,
            prefix="action_generate_conda_export: ",
        ),
    )

    conda_prefix_export = yaml.dump(context.result).encode("utf-8")

    build_context.conda_store.plugin_manager.hook.storage_set(
        db=build_context.db,
        build_id=build.id,
        key=build.conda_env_export_key,
        value=conda_prefix_export,
        content_type="text/yaml",
        artifact_type=schema.BuildArtifactType.YAML,
    )


# TODO: replace with artifact plugin
@build_context.build_task
def build_conda_pack(build_context, build: orm.Build):
    conda_prefix = build.build_path(build_context.conda_store)

    with utils.timer(
        build_context.conda_store.log, f"packaging archive of conda environment={conda_prefix}"
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_filename = pathlib.Path(tmpdir) / "environment.tar.gz"
            action.action_generate_conda_pack(
                conda_prefix=conda_prefix,
                output_filename=output_filename,
                stdout=LoggedStream(
                    db=build_context.db,
                    conda_store=build_context.conda_store,
                    build=build,
                    prefix="action_generate_conda_pack: ",
                ),
            )
            build_context.conda_store.plugin_manager.hook.storage_fset(
                db=build_context.db,
                build_id=build.id,
                key=build.conda_pack_key,
                filename=output_filename,
                content_type="application/gzip",
                artifact_type=schema.BuildArtifactType.CONDA_PACK,
            )


# TODO: replace with artifact plugin
@build_context.build_task
def build_conda_docker(build_context, build: orm.Build):
    import warnings

    warnings.warn(
        "Generating Docker images is currently not supported, see "
        "https://github.com/conda-incubator/conda-store/issues/666"
    )
    return

    conda_prefix = build.build_path(conda_store)
    settings = conda_store.get_settings(
        db=db,
        namespace=build.environment.namespace.name,
        environment_name=build.environment.name,
    )

    try:
        with utils.timer(
            conda_store.log,
            f"packaging docker image of conda environment={conda_prefix}",
        ):
            context = action.action_generate_conda_docker(
                conda_prefix=conda_prefix,
                default_docker_image=utils.callable_or_value(
                    settings.default_docker_base_image, None
                ),
                container_registry=conda_store.container_registry,
                output_image_name=build.specification.name,
                output_image_tag=build.build_key,
            )
            append_to_logs(
                db,
                conda_store,
                build,
                "::group::action_generate_conda_docker\n"
                + context.stdout.getvalue()
                + "\n::endgroup::\n",
            )

            image = context.result

            if schema.BuildArtifactType.DOCKER_MANIFEST in settings.build_artifacts:
                conda_store.container_registry.store_image(
                    db, conda_store, build, image
                )

            if schema.BuildArtifactType.CONTAINER_REGISTRY in settings.build_artifacts:
                conda_store.container_registry.push_image(db, build, image)
    except Exception as e:
        conda_store.log.exception(e)
        append_to_logs(db, conda_store, build, traceback.format_exc())
        raise e



# TODO: replace with artifact plugin
@build_context.build_task
def build_constructor_installer(build_context, build: orm.Build):
    conda_prefix = build.build_path(build_context.conda_store)

    settings = build_context.conda_store.get_settings(
        db=build_context.db,
        namespace=build.environment.namespace.name,
        environment_name=build.environment.name,
    )

    with utils.timer(
        build_context.conda_store.log, f"creating installer for conda environment={conda_prefix}"
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            is_lockfile = build.specification.is_lockfile

            if is_lockfile:
                specification = schema.LockfileSpecification.parse_obj(
                    build.specification.spec
                )
            else:
                try:
                    # Tries to use the lockfile if it's available since it has
                    # pinned dependencies. This code is wrapped into try/except
                    # because the lockfile lookup might fail if the file is not
                    # in external storage or on disk, or if parsing fails
                    specification = schema.LockfileSpecification.parse_obj(
                        {
                            "name": build.specification.name,
                            "lockfile": json.loads(
                               build_context.conda_store.plugin_manager.hook.storage_get(key=build.conda_lock_key)
                            ),
                        }
                    )
                    is_lockfile = True
                except Exception as e:
                    build_context.conda_store.log.warning(
                        "Exception while obtaining lockfile, using specification",
                        exc_info=e,
                    )
                    specification = schema.CondaSpecification.parse_obj(
                        build.specification.spec
                    )

            context = action.action_generate_constructor_installer(
                conda_command=settings.conda_command,
                specification=specification,
                installer_dir=pathlib.Path(tmpdir),
                version=build.build_key,
                stdout=LoggedStream(
                    db=build_context.db,
                    conda_store=build_context.conda_store,
                    build=build,
                    prefix="action_generate_constructor_installer: ",
                ),
                is_lockfile=is_lockfile,
            )
            output_filename = context.result
            if output_filename is None:
                return
            build_context.conda_store.plugin_manager.hook.storage_fset(
                db=build_context.db,
                build_id=build.id,
                key=build.constructor_installer_key,
                value=output_filename,
                content_type="application/octet-stream",
                artifact_type=schema.BuildArtifactType.CONSTRUCTOR_INSTALLER,
            )
