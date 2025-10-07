from app import create_app
from app.config import TestConfig
import os

def test_health(tmp_path):
    os.environ["TEST_STORAGE_ROOT"] = str(tmp_path)
    app = create_app(TestConfig)
    client = app.test_client()
    r = client.get("/api/v1/health")
    assert r.status_code == 200
