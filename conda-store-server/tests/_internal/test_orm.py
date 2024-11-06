# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pytest
from unittest import mock

from conda_store_server import api
from conda_store_server._internal import conda_utils, orm, schema, utils


@pytest.fixture
def populated_db(db):
    """A database fixture populated with TODO: what is this populated with"""
    # Create test channels
    api.create_conda_channel(db, "test-channel-1")
    api.create_conda_channel(db, "test-channel-2")
    db.commit()

    # Create some sample conda_package's
    conda_package_records = [
        {
            "channel_id": 1,
            "name": "test-package-1",
            "version": "1.0.0",
            "license": "",
            "license_family": "",
            "summary": "",
            "description": "",
        },
    ]
    for conda_package_record in conda_package_records:
        api.create_conda_package(db, conda_package_record)
    db.commit()

    # Create some conda_package_build's
    conda_package_builds = [
        (1, {
            "build": "py310h06a4308_0",
            "channel_id": 1,
            "build_number": 0,
            "sha256": "11f080b53b36c056dbd86ccd6dc56c40e3e70359f64279b1658bb69f91ae726f",
            "subdir": "linux-64",
            "constrains": "",
            "md5": "",
            "depends": "",
            "timestamp": "",
            "size": "",
        }),
        (1, {
            "build": "py311h06a4308_0",
            "channel_id": 1,
            "build_number": 0,
            "sha256": "f0719ee6940402a1ea586921acfaf752fda977dbbba74407856a71ba7f6c4e4a",
            "subdir": "linux-64",
            "constrains": "",
            "md5": "",
            "depends": "",
            "timestamp": "",
            "size": "",
        }),
        (1, {
            "build": "py38h06a4308_0",
            "channel_id": 1,
            "build_number": 0,
            "sha256": "39e39a23baebd0598c1b59ae0e82b5ffd6a3230325da4c331231d55cbcf13b3e",
            "subdir": "linux-64",
            "constrains": "",
            "md5": "",
            "depends": "",
            "timestamp": "",
            "size": "",
        })
    ]
    for cpb in conda_package_builds:
        conda_package_build = orm.CondaPackageBuild(
            package_id=cpb[0],
            **cpb[1],
        )
        db.add(conda_package_build)
    db.commit()
    
    return db

test_repodata = {
    "architectures": {
       "linux-64": {
             "packages": {
                "test-package-1-0.1.0-py310_0.tar.bz2": {
                "build": "py37_0",
                "build_number": 0,
                "depends": [
                    "some-depends"
                ],
                "license": "BSD",
                "md5": "a75683f8d9f5b58c19a8ec5d0b7f796e",
                "name": "test-package-1",
                "sha256": "1fe3c3f4250e51886838e8e0287e39029d601b9f493ea05c37a2630a9fe5810f",
                "size": 3832,
                "subdir": "win-64",
                "timestamp": 1530731681870,
                "version": "0.1.0"
                },
            }
        }
    }
}


@mock.patch("conda_store_server._internal.conda_utils.download_repodata")
def test_update_packages_first_time(mock_repdata, db):
    # mock download_repodata to return static test repodata
    mock_repdata.return_value = test_repodata

    # create test channel
    channel = api.create_conda_channel(db, "test-channel-1")

    channel.update_packages(db, "linux-64")

    # ensure the package is added
    conda_packages = db.query(orm.CondaPackage).all()
    assert len(conda_packages) == 1

    conda_packages = db.query(orm.CondaPackageBuild).all()
    assert len(conda_packages) == 1


@mock.patch("conda_store_server._internal.conda_utils.download_repodata")
def test_update_packages_add_existing_pkg(mock_repdata, populated_db):
    # mock download_repodata to return static test repodata
    mock_repdata.return_value = test_repodata

    channel = populated_db.query(orm.CondaChannel).filter(orm.CondaChannel.id == 1).first()
    channel.update_packages(populated_db, "linux-64")

    # ensure the package is added
    conda_packages = populated_db.query(orm.CondaPackage).filter(orm.CondaPackage.channel_id == 1).all()
    assert len(conda_packages) == 2

    conda_packages = populated_db.query(orm.CondaPackageBuild).filter(orm.CondaPackageBuild.channel_id == 1).all()
    assert len(conda_packages) == 4


@mock.patch("conda_store_server._internal.conda_utils.download_repodata")
def test_update_packages_new_package_channel(mock_repdata, populated_db):
    # mock download_repodata to return static test repodata
    mock_repdata.return_value = test_repodata

    channel = populated_db.query(orm.CondaChannel).filter(orm.CondaChannel.id == 2).first()
    channel.update_packages(populated_db, "linux-64")

    # ensure the package is added
    conda_packages = populated_db.query(orm.CondaPackage).filter(orm.CondaPackage.channel_id == 2).all()
    assert len(conda_packages) == 1

    conda_packages = populated_db.query(orm.CondaPackageBuild).filter(orm.CondaPackageBuild.channel_id == 2).all()
    assert len(conda_packages) == 1
