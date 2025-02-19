# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
from __future__ import annotations

import re
from typing import Any, Dict, List, Union

from sqlalchemy import distinct, func, null, or_
from sqlalchemy.orm import Query, aliased, session

from conda_store_server._internal import conda_utils, orm, schema, utils
from conda_store_server._internal.environment import filter_environments
from conda_store_server.server import schema as auth_schema


def list_namespaces(db, show_soft_deleted: bool = False):
    filters = []
    if not show_soft_deleted:
        filters.append(orm.Namespace.deleted_on == null())

    return db.query(orm.Namespace).filter(*filters)


def ensure_namespace(db, name: str):
    namespace = get_namespace(db, name=name)
    if namespace is None:
        namespace = create_namespace(db, name=name)
        db.commit()
    return namespace


def get_namespace(
    db, name: str = None, id: int = None, show_soft_deleted: bool = True
) -> orm.Namespace:
    filters = []
    if name:
        filters.append(orm.Namespace.name == name)
    if id:
        filters.append(orm.Namespace.id == id)
    if not show_soft_deleted:
        filters.append(orm.Namespace.deleted_on == null())
    return db.query(orm.Namespace).filter(*filters).first()


def create_namespace(db, name: str):
    if re.fullmatch(f"[{schema.ALLOWED_CHARACTERS}]+", name) is None:
        raise ValueError(
            f"Namespace='{name}' is not valid does not match regex {schema.NAMESPACE_REGEX}"
        )

    namespace = orm.Namespace(name=name)
    db.add(namespace)
    return namespace


def update_namespace(
    db,
    name: str,
    metadata_: Dict[str, Any] = None,
    role_mappings: Dict[str, List[str]] = None,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    if metadata_ is not None:
        namespace.metadata_ = metadata_

    if role_mappings is not None:
        # deletes all the existing role mappings ...
        for rm in namespace.role_mappings:
            db.delete(rm)

        # ... before adding all the new ones
        mappings_orm = []
        for entity, roles in role_mappings.items():
            for role in roles:
                mapping_orm = orm.NamespaceRoleMapping(
                    namespace_id=namespace.id,
                    namespace=namespace,
                    entity=entity,
                    role=role,
                )
                mappings_orm.append(mapping_orm)

        namespace.role_mappings = mappings_orm

    db.commit()

    return namespace


# v2 API
def update_namespace_metadata(
    db,
    name: str,
    metadata_: Dict[str, Any] = None,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    if metadata_ is not None:
        namespace.metadata_ = metadata_

    return namespace


# v2 API
def get_namespace_roles(
    db,
    name: str,
) -> list[schema.NamespaceRoleMappingV2]:
    """Which namespaces can access namespace 'name'?"""
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    nrm = aliased(orm.NamespaceRoleMappingV2)
    this = aliased(orm.Namespace)
    other = aliased(orm.Namespace)
    q = (
        db.query(nrm.id, this.name, other.name, nrm.role)
        .filter(nrm.namespace_id == namespace.id)
        .filter(nrm.namespace_id == this.id)
        .filter(nrm.other_namespace_id == other.id)
        .all()
    )
    return [schema.NamespaceRoleMappingV2.from_list(x) for x in q]


# v2 API
def get_other_namespace_roles(
    db,
    name: str,
):
    """To which namespaces does namespace 'name' have access?"""
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    nrm = aliased(orm.NamespaceRoleMappingV2)
    this = aliased(orm.Namespace)
    other = aliased(orm.Namespace)
    q = (
        db.query(nrm.id, this.name, other.name, nrm.role)
        .filter(nrm.other_namespace_id == namespace.id)
        .filter(nrm.namespace_id == this.id)
        .filter(nrm.other_namespace_id == other.id)
        .all()
    )
    return [schema.NamespaceRoleMappingV2.from_list(x) for x in q]


# v2 API
def delete_namespace_roles(
    db,
    name: str,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    nrm = orm.NamespaceRoleMappingV2
    db.query(nrm).filter(nrm.namespace_id == namespace.id).delete()


# v2 API
def get_namespace_role(
    db,
    name: str,
    other: str,
) -> schema.NamespaceRoleMappingV2 | None:
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    other_namespace = get_namespace(db, other)
    if other_namespace is None:
        raise ValueError(f"Namespace='{other}' not found")

    nrm = aliased(orm.NamespaceRoleMappingV2)
    this = aliased(orm.Namespace)
    other = aliased(orm.Namespace)
    q = (
        db.query(nrm.id, this.name, other.name, nrm.role)
        .filter(nrm.namespace_id == namespace.id)
        .filter(nrm.other_namespace_id == other_namespace.id)
        .filter(nrm.namespace_id == this.id)
        .filter(nrm.other_namespace_id == other.id)
        .first()
    )
    if q is None:
        return None
    return schema.NamespaceRoleMappingV2.from_list(q)


# v2 API
def create_namespace_role(
    db,
    name: str,
    other: str,
    role: str,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    other_namespace = get_namespace(db, other)
    if other_namespace is None:
        raise ValueError(f"Namespace='{other}' not found")

    db.add(
        orm.NamespaceRoleMappingV2(
            namespace_id=namespace.id,
            other_namespace_id=other_namespace.id,
            role=role,
        )
    )


# v2 API
def update_namespace_role(
    db,
    name: str,
    other: str,
    role: str,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    other_namespace = get_namespace(db, other)
    if other_namespace is None:
        raise ValueError(f"Namespace='{other}' not found")

    nrm = orm.NamespaceRoleMappingV2
    q = (
        db.query(nrm)
        .filter(nrm.namespace_id == namespace.id)
        .filter(nrm.other_namespace_id == other_namespace.id)
        .first()
    )
    # Important: this modifies a field of a table entry and calls 'db.add'
    # instead of using '.update({"role": role})' on the query because the latter
    # would bypass the ORM validation logic, which maps the 'editor' role to
    # 'developer'
    q.role = role
    db.add(q)


# v2 API
def delete_namespace_role(
    db,
    name: str,
    other: str,
):
    namespace = get_namespace(db, name)
    if namespace is None:
        raise ValueError(f"Namespace='{name}' not found")

    other_namespace = get_namespace(db, other)
    if other_namespace is None:
        raise ValueError(f"Namespace='{other}' not found")

    nrm = orm.NamespaceRoleMappingV2
    db.query(nrm).filter(nrm.namespace_id == namespace.id).filter(
        nrm.other_namespace_id == other_namespace.id
    ).delete()


def delete_namespace(db, name: str = None, id: int = None):
    namespace = get_namespace(db, name=name, id=id)
    if namespace:
        db.delete(namespace)


def list_environments(
    db: session.Session,
    namespace: str = None,
    name: str = None,
    status: schema.BuildStatus = None,
    packages: List[str] = None,
    artifact: schema.BuildArtifactType = None,
    search: str = None,
    show_soft_deleted: bool = False,
    role_bindings: auth_schema.RoleBindings | None = None,
) -> Query:
    """Retrieve all environments managed by conda-store.

    Parameters
    ----------
    db : session.Session
        Database to query for environments
    namespace : str | None
        If specified, filter by environments in the given namespace
    name : str | None
        If specified, filter by environments with the given name
    status : schema.BuildStatus
        If specified, filter by environments with the given status
    packages : List[str] | None
        If specified, filter by environments containing the given package name(s)
    artifact : schema.BuildArtifactType | None
        If specified, filter by environments with the given BuildArtifactType
    search : str | None
        If specified, filter by environment names or namespace names containing the
        search term
    show_soft_deleted : bool
        If specified, filter by environments which have a null value for the
        deleted_on attribute
    role_bindings : auth_schema.RoleBindings | None
        If specified, filter by only the environments the given role_bindings
        have read, write, or admin access to. This should be the same object as
        the role bindings in conda_store_config.py, for example:

            {
                "*/*": ['admin'],
                ...
            }

    Returns
    -------
    Query
        Sqlalchemy query containing the requested environments
    """
    query = db.query(orm.Environment).join(orm.Environment.namespace)

    if namespace:
        query = query.filter(orm.Namespace.name == namespace)

    if name:
        query = query.filter(orm.Environment.name == name)

    if search:
        query = query.filter(
            or_(
                orm.Namespace.name.contains(search, autoescape=True),
                orm.Environment.name.contains(search, autoescape=True),
            )
        )

    if not show_soft_deleted:
        query = query.filter(orm.Environment.deleted_on == null())

    if status or artifact or packages:
        query = query.join(orm.Environment.current_build)

    if status:
        query = query.filter(orm.Build.status == status)

    if artifact:
        query = query.join(orm.Build.build_artifacts).filter(
            orm.BuildArtifact.artifact_type == artifact
        )

    if packages:
        query = (
            query.join(orm.Build.package_builds)
            .join(orm.CondaPackageBuild.package)
            .filter(orm.CondaPackage.name.in_(packages))
            .group_by(orm.Namespace.name, orm.Environment.name, orm.Environment.id)
            .having(func.count() == len(packages))
        )

    if role_bindings:
        # Any entity binding is sufficient permissions to view an environment;
        # no entity binding will hide the environment
        query = filter_environments(query, role_bindings)

    return query


def ensure_environment(
    db,
    name: str,
    namespace_id: int,
    description: str = None,
):
    environment = get_environment(db, name=name, namespace_id=namespace_id)
    if environment is None:
        environment = create_environment(
            db, name=name, namespace_id=namespace_id, description=description
        )
        db.commit()
    elif description:
        update_environment(
            db, name=name, namespace_id=namespace_id, description=description
        )
        db.commit()
    return environment


def create_environment(db, name: str, namespace_id: int, description: str):
    environment = orm.Environment(
        name=name, namespace_id=namespace_id, description=description
    )
    db.add(environment)
    return environment


def update_environment(db, name: str, namespace_id: int, description: str):
    environment = get_environment(db, name=name, namespace_id=namespace_id)
    environment.description = description
    return environment


def get_environment(
    db,
    name: str = None,
    namespace: str = None,
    namespace_id: int = None,
    id: int = None,
):
    filters = []
    if namespace:
        filters.append(orm.Namespace.name == namespace)
    if namespace_id:
        filters.append(orm.Namespace.id == namespace_id)
    if name:
        filters.append(orm.Environment.name == name)
    if id:
        filters.append(orm.Environment.id == id)

    return db.query(orm.Environment).join(orm.Namespace).filter(*filters).first()


def ensure_specification(
    db,
    specification: Union[schema.CondaSpecification, schema.LockfileSpecification],
    is_lockfile: bool = False,
):
    specification_sha256 = utils.datastructure_hash(specification.model_dump())
    specification_orm = get_specification(db, sha256=specification_sha256)

    if specification_orm is None:
        specification_orm = create_speficication(
            db, specification, is_lockfile=is_lockfile
        )
        db.commit()

    return specification_orm


def create_speficication(
    db,
    specification: Union[schema.CondaSpecification, schema.LockfileSpecification],
    is_lockfile: bool = False,
):
    specification_orm = orm.Specification(
        specification.model_dump(), is_lockfile=is_lockfile
    )
    db.add(specification_orm)
    return specification_orm


def list_specifications(db, search=None):
    filters = []
    return db.query(orm.Specification).filter(*filters)


def get_specification(db, sha256: str):
    filters = [orm.Specification.sha256 == sha256]
    return db.query(orm.Specification).filter(*filters).first()


def create_solve(db, specification_id: int):
    solve = orm.Solve(specification_id=specification_id)
    db.add(solve)
    return solve


def get_solve(db, solve_id: int):
    return db.query(orm.Solve).filter(orm.Solve.id == solve_id).first()


def list_solves(db):
    return db.query(orm.Solve)


def list_builds(
    db,
    status: schema.BuildStatus = None,
    packages: List[str] = None,
    artifact: schema.BuildArtifactType = None,
    environment_id: str = None,
    name: str = None,
    namespace: str = None,
    show_soft_deleted: bool = False,
):
    query = (
        db.query(orm.Build).join(orm.Build.environment).join(orm.Environment.namespace)
    )

    if status:
        query = query.filter(orm.Build.status == status)

    if environment_id:
        query = query.filter(orm.Build.environment_id == environment_id)

    if name:
        query = query.filter(orm.Environment.name == name)

    if namespace:
        query = query.filter(orm.Namespace.name == namespace)

    if not show_soft_deleted:
        query = query.filter(orm.Build.deleted_on == null())

    if artifact:
        query = query.join(orm.Build.build_artifacts).filter(
            orm.BuildArtifact.artifact_type == artifact
        )

    if packages:
        query = (
            query.join(orm.Build.packages)
            .filter(orm.CondaPackage.name.in_(packages))
            .group_by(orm.Build.id)
            .having(func.count() == len(packages))
        )

    return query


def create_build(db, environment_id: int, specification_id: int):
    build = orm.Build(environment_id=environment_id, specification_id=specification_id)
    db.add(build)
    return build


def get_build(db, build_id: int):
    return db.query(orm.Build).filter(orm.Build.id == build_id).first()


def get_build_packages(
    db, build_id: int, search: str = None, exact: bool = False, build: str = None
):
    filters = [(orm.Build.id == build_id)]
    if search:
        if exact:
            filters.append(orm.CondaPackage.name.like(search.replace("%", r"\%")))
        else:
            filters.append(orm.CondaPackage.name.contains(search, autoescape=True))
    if build:
        filters.append(orm.CondaPackageBuild.build.contains(build, autoescape=True))

    return (
        db.query(orm.CondaPackage)
        .join(orm.Build.package_builds)
        .join(orm.CondaPackageBuild.package)
        .join(orm.CondaPackage.channel)
        .filter(*filters)
    )


def get_build_lockfile_legacy(db, build_id: int):
    build = db.query(orm.Build).filter(orm.Build.id == build_id).first()
    packages = [
        f"{row.package.channel.name}/{row.subdir}/{row.package.name}-{row.package.version}-{row.build}.tar.bz2#{row.md5}"
        for row in build.package_builds
    ]
    return """#platform: {0}
@EXPLICIT
{1}
""".format(conda_utils.conda_platform(), "\n".join(packages))


def get_build_artifact_types(db, build_id: int):
    return (
        db.query(orm.BuildArtifact.artifact_type)
        .filter(orm.BuildArtifact.build_id == build_id)
        .distinct()
    )


def list_build_artifacts(
    db,
    build_id: int = None,
    key: str = None,
    excluded_artifact_types: List[schema.BuildArtifactType] = None,
    included_artifact_types: List[schema.BuildArtifactType] = None,
):
    filters = []
    if build_id:
        filters.append(orm.BuildArtifact.build_id == build_id)
    if key:
        filters.append(orm.BuildArtifact.key == key)
    if excluded_artifact_types:
        filters.append(
            func.not_(orm.BuildArtifact.artifact_type.in_(excluded_artifact_types))
        )
    if included_artifact_types:
        filters.append(orm.BuildArtifact.artifact_type.in_(included_artifact_types))

    return db.query(orm.BuildArtifact).filter(*filters)


def get_build_artifact(db, build_id: int, key: str):
    return (
        db.query(orm.BuildArtifact)
        .filter(orm.BuildArtifact.build_id == build_id, orm.BuildArtifact.key == key)
        .first()
    )


def ensure_conda_channel(db, channel_name: str):
    conda_channel = get_conda_channel(db, channel_name)
    if conda_channel is None:
        conda_channel = create_conda_channel(db, channel_name)
        db.commit()
    return conda_channel


def list_conda_channels(db):
    filters = []
    return db.query(orm.CondaChannel).filter(*filters)


def create_conda_channel(db, channel_name: str):
    channel = orm.CondaChannel(name=channel_name, last_update=None)
    db.add(channel)
    return channel


def get_conda_channel(db, channel_name: str):
    return (
        db.query(orm.CondaChannel).filter(orm.CondaChannel.name == channel_name).first()
    )


def get_conda_package(db, channel_id: int, name: str, version: str):
    return (
        db.query(orm.CondaPackage)
        .filter(orm.CondaPackage.channel_id == channel_id)
        .filter(orm.CondaPackage.name == name)
        .filter(orm.CondaPackage.version == version)
        .first()
    )


def get_conda_package_build(db, package_id: int, subdir: str, build: str):
    return (
        db.query(orm.CondaPackageBuild)
        .filter(orm.CondaPackageBuild.package_id == package_id)
        .filter(orm.CondaPackageBuild.subdir == subdir)
        .filter(orm.CondaPackageBuild.build == build)
        .first()
    )


def create_or_ignore_conda_package(db, package_record: Dict):
    # first create the conda channel
    channel = package_record["channel_id"]
    if channel == "https://conda.anaconda.org/pypi":
        # ignore pypi package for now
        return None

    channel_orm = get_conda_channel(db, channel)
    if channel_orm is None:
        channel_orm = create_conda_channel(db, channel)
        db.commit()

    package_record["channel_id"] = channel_orm.id

    # Retrieve the package from the DB if it already exists
    conda_package = get_conda_package(
        db,
        channel_id=package_record["channel_id"],
        name=package_record["name"],
        version=package_record["version"],
    )

    # If it doesn't exist, let's create it in DB
    if conda_package is None:
        conda_package = create_conda_package(db, package_record=package_record)

    # Retrieve the build for this pacakge, if it already exists
    conda_package_build = get_conda_package_build(
        db,
        package_id=conda_package.id,
        subdir=package_record["subdir"],
        build=package_record["build"],
    )

    # If it doesn't exist, let's create it in DB
    if conda_package_build is None:
        conda_package_build = create_conda_package_build(
            db,
            package_id=conda_package.id,
            package_record=package_record,
        )

    return conda_package_build


def create_conda_package(db, package_record: Dict):
    conda_package_keys = [
        "channel_id",
        "license",
        "license_family",
        "name",
        "version",
        "summary",
        "description",
    ]

    conda_package = orm.CondaPackage(
        **{k: package_record[k] for k in conda_package_keys}
    )
    db.add(conda_package)
    return conda_package


def create_conda_package_build(db, package_id: int, package_record: Dict):
    conda_package_build_keys = [
        "build",
        "build_number",
        "constrains",
        "depends",
        "md5",
        "sha256",
        "size",
        "subdir",
        "timestamp",
    ]
    conda_package_build = orm.CondaPackageBuild(
        package_id=package_id,
        **{k: package_record[k] for k in conda_package_build_keys},
    )
    db.add(conda_package_build)
    return conda_package_build


def list_conda_packages(db, search: str = None, exact: bool = False, build: str = None):
    filters = []
    if search:
        if exact:
            filters.append(orm.CondaPackage.name.like(search.replace("%", r"\%")))
        else:
            filters.append(orm.CondaPackage.name.contains(search, autoescape=True))
    if build:
        filters.append(orm.CondaPackage.build.contains(build, autoescape=True))

    return db.query(orm.CondaPackage).join(orm.CondaChannel).filter(*filters)


def get_metrics(db):
    metrics = (
        db.query(
            orm.CondaStoreConfiguration.free_storage.label("disk_free"),
            orm.CondaStoreConfiguration.total_storage.label("disk_total"),
            orm.CondaStoreConfiguration.disk_usage,
        )
        .first()
        ._asdict()
    )

    query = db.query(func.count(orm.Build.status), orm.Build.status).group_by(
        orm.Build.status
    )
    for build_count, build_status_enum in query.all():
        metrics[f"build_{build_status_enum.value.lower()}"] = build_count

    metrics["environments"] = db.query(orm.Environment).count()
    return metrics


def get_system_metrics(db):
    return db.query(
        orm.CondaStoreConfiguration.free_storage.label("disk_free"),
        orm.CondaStoreConfiguration.total_storage.label("disk_total"),
        orm.CondaStoreConfiguration.disk_usage,
    ).first()


def get_namespace_metrics(db):
    return (
        db.query(
            orm.Namespace.name,
            func.count(distinct(orm.Environment.id)),
            func.count(distinct(orm.Build.id)),
            func.sum(orm.Build.size),
        )
        .join(orm.Build.environment)
        .join(orm.Environment.namespace)
        .group_by(orm.Namespace.name)
    )


def get_kvstore_key_values(db, prefix: str):
    """Get effective key, values for a particular prefix"""
    return {
        _.key: _.value
        for _ in db.query(orm.KeyValueStore)
        .filter(orm.KeyValueStore.prefix == prefix)
        .all()
    }


def get_kvstore_key(db, prefix: str, key: str):
    """Get value for a particular prefix and key"""
    row = (
        db.query(orm.KeyValueStore)
        .filter(orm.KeyValueStore.prefix == prefix)
        .filter(orm.KeyValueStore.key == key)
        .first()
    )
    if row is None:
        return None
    return row.value


def set_kvstore_key_values(db, prefix: str, d: Dict[str, Any], update: bool = True):
    """Set key, values for a particular prefix"""
    for key, value in d.items():
        record = (
            db.query(orm.KeyValueStore)
            .filter(orm.KeyValueStore.prefix == prefix, orm.KeyValueStore.key == key)
            .first()
        )

        if record is None:
            record = orm.KeyValueStore(
                prefix=prefix,
                key=key,
                value=value,
            )
            db.add(record)
            db.commit()
        elif update:
            record.value = value
            db.commit()
