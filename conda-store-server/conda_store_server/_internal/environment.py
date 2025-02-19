# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pathlib

import pydantic
import yaml
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from conda_store_server._internal import conda_utils, orm, schema, utils
from conda_store_server.server import schema as auth_schema


def validate_environment(specification):
    try:
        specification = schema.CondaSpecification.model_validate(specification)
        return True
    except pydantic.ValidationError:
        return False


def is_environment_file(filename):
    if str(filename).endswith(".yaml") or str(filename).endswith(".yml"):
        with filename.open() as f:
            return validate_environment(yaml.safe_load(f))
    else:
        return False


def discover_environments(paths):
    environments = []
    for path in paths:
        path = pathlib.Path(path).resolve()
        if path.is_file() and is_environment_file(path):
            environments.append(path)
        elif path.is_dir():
            for _path in path.glob("*"):
                if is_environment_file(_path):
                    environments.append(_path)
    return environments


def validate_environment_channels(
    specification: schema.Specification, settings: schema.Settings
) -> schema.Specification:
    if len(specification.channels) == 0:
        specification.channels = settings.conda_default_channels.copy()

    normalized_conda_channels = set(
        conda_utils.normalize_channel_name(settings.conda_channel_alias, _)
        for _ in specification.channels
    )

    normalized_conda_allowed_channels = set(
        conda_utils.normalize_channel_name(settings.conda_channel_alias, _)
        for _ in settings.conda_allowed_channels
    )

    if len(settings.conda_allowed_channels) and not (
        normalized_conda_channels <= normalized_conda_allowed_channels
    ):
        raise ValueError(
            f"Conda channels {normalized_conda_channels - normalized_conda_allowed_channels} not allowed in specification"
        )

    return specification


def validate_environment_conda_packages(
    specification: schema.Specification, settings: schema.Settings
) -> schema.Specification:
    def _package_names(dependencies):
        from conda.models.match_spec import MatchSpec

        return {MatchSpec(_).name: _ for _ in dependencies if isinstance(_, str)}

    if len(specification.dependencies) == 0:
        specification.dependencies = settings.conda_default_packages.copy()

    _included_packages = _package_names(settings.conda_included_packages)
    for package in (
        _included_packages.keys() - _package_names(specification.dependencies).keys()
    ):
        specification.dependencies.append(_included_packages[package])

    missing_packages = (
        _package_names(settings.conda_required_packages).keys()
        <= _package_names(specification.dependencies).keys()
    )
    if not missing_packages:
        raise ValueError(
            f"Conda packages {missing_packages} required and missing from specification"
        )

    return specification


def validate_environment_pypi_packages(
    specification: schema.Specification, settings: schema.Settings
) -> schema.Specification:
    def _package_names(packages):
        from pkg_resources import Requirement

        result = {}
        for p in packages:
            if isinstance(p, str):
                if p.startswith("--"):
                    result[p] = p
                else:
                    result[Requirement.parse(p).name] = p
        return result

    def _get_pip_packages(specification):
        for package in specification.dependencies:
            if isinstance(package, schema.CondaSpecificationPip):
                return package.pip
        return []

    def _append_pip_packages(specification, packages):
        for package in specification.dependencies:
            if isinstance(package, schema.CondaSpecificationPip):
                package.pip += packages
                return
        specification.dependencies.append(schema.CondaSpecificationPip(pip=packages))

    if (
        len(_get_pip_packages(specification)) == 0
        and len(settings.pypi_default_packages) != 0
    ):
        _append_pip_packages(specification, settings.pypi_default_packages)

    _included_packages = _package_names(settings.pypi_included_packages)
    for package in (
        _included_packages.keys()
        - _package_names(_get_pip_packages(specification)).keys()
    ):
        _append_pip_packages(specification, [_included_packages[package]])

    missing_packages = (
        _package_names(settings.pypi_required_packages).keys()
        <= _package_names(_get_pip_packages(specification)).keys()
    )
    if not missing_packages:
        raise ValueError(
            f"PyPi packages {missing_packages} required and missing from specification"
        )

    return specification


def filter_environments(
    query: Query,
    role_bindings: auth_schema.RoleBindings,
) -> Query:
    """Filter a query containing environments and namespaces by a set of role bindings.

    Parameters
    ----------
    query : Query
        Query containing both environments and namespaces
    role_bindings : auth_schema.RoleBindings
        Role bindings to filter the results by

    Returns
    -------
    Query
        A query containing only the environments and namespaces accessible to the
        given role bindings
    """
    cases = []
    for entity_arn, entity_roles in role_bindings.items():
        namespace, name = utils.compile_arn_sql_like(
            entity_arn, auth_schema.ARN_ALLOWED_REGEX
        )
        cases.append(
            and_(
                orm.Namespace.name.like(namespace),
                orm.Environment.name.like(name),
            )
        )

    if not cases:
        return query.filter(False)

    return query.join(orm.Environment.namespace).filter(or_(*cases))
