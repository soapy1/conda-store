# Copyright (c) conda-store development team. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import logging
import os

import uvicorn

import conda_store_server

from conda_store_server._internal.server.app import CondaStoreServer


logger = logging.getLogger(__name__)

server = CondaStoreServer.launch_instance()
logger.info(f"Starting server on {server.address}:{server.port}")

app = server.init_fastapi_app()


def main():
    uvicorn.run(
        "conda_store_server._internal.server.__main__:app",
        host=server.address,
        port=server.port,
        workers=1,
        proxy_headers=server.behind_proxy,
        forwarded_allow_ips=("*" if server.behind_proxy else None),
        reload=server.reload,
        reload_dirs=(
            [os.path.dirname(conda_store_server.__file__)] if server.reload else []
        ),
    )
