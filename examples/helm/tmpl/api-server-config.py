import logging
import os

from conda_store_server.server.auth import DummyAuthentication
from conda_store_server.storage import S3Storage

# ==================================
#      conda-store settings
# ==================================
c.CondaStore.storage_threshold = 1024
c.CondaStore.storage_class = S3Storage
c.CondaStore.store_directory = "/opt/conda-store/conda-store/"
c.CondaStore.database_url = f"postgresql+psycopg2://{os.environ.get('POSTGRES_USERNAME')}:{os.environ.get('POSTGRES_PASSWORD')}@postgres/conda-store"
c.CondaStore.redis_url =   (
    f"redis://:{os.environ.get('REDIS_PASSWORD')}@redis:6379/0"
)
c.CondaStore.default_uid = 1000
c.CondaStore.default_gid = 100
c.CondaStore.default_permissions = "555"
c.CondaStore.conda_included_packages = ["ipykernel"]
c.CondaStore.default_namespace = "global"
c.CondaStore.filesystem_namespace = "conda-store"
c.CondaStore.conda_allowed_channels = []  # allow all channels
c.CondaStore.conda_indexed_channels = [
    "main",
    "conda-forge",
    "https://repo.anaconda.com/pkgs/main",
]

# ==================================
#      s3 settings
# ==================================
c.S3Storage.internal_endpoint = "minio:9000"
c.S3Storage.internal_secure = False
c.S3Storage.external_endpoint = "localhost:9000"
c.S3Storage.external_secure = False
c.S3Storage.access_key = os.environ.get('MINIO_USERNAME')
c.S3Storage.secret_key = os.environ.get('MINIO_PASSWORD')
c.S3Storage.region = "us-east-1"  # minio region default
c.S3Storage.bucket_name = "conda-store"

c.RBACAuthorizationBackend.role_mappings_version = 2

# ==================================
#        server settings
# ==================================
c.CondaStoreServer.log_level = logging.INFO
c.CondaStoreServer.log_format = (
    "%(asctime)s %(levelname)9s %(name)s:%(lineno)4s: %(message)s"
)
c.CondaStoreServer.enable_ui = False
c.CondaStoreServer.enable_api = True
c.CondaStoreServer.enable_registry = False
c.CondaStoreServer.enable_metrics = True
c.CondaStoreServer.address = "0.0.0.0"
c.CondaStoreServer.port = 8080
c.CondaStoreServer.behind_proxy = True
# This MUST start with `/`
c.CondaStoreServer.url_prefix = "/"

# ==================================
#         auth settings
# ==================================
c.CondaStoreServer.authentication_class = DummyAuthentication