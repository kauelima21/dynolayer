import pytest

from dynolayer.config import DynoConfig
from dynolayer.crud_mixin import CrudMixin
from dynolayer.dynolayer import DynoLayer


class TestDynoConfig:
    def test_default_values(self):
        assert DynoConfig.get("region") == "sa-east-1"
        assert DynoConfig.get("endpoint_url") is None
        assert DynoConfig.get("aws_access_key_id") is None
        assert DynoConfig.get("aws_secret_access_key") is None
        assert DynoConfig.get("profile_name") is None
        assert DynoConfig.get("timestamp_format") == "numeric"
        assert DynoConfig.get("timestamp_timezone") == "America/Sao_Paulo"
        assert DynoConfig.get("retry_max_attempts") == 3
        assert DynoConfig.get("retry_mode") == "adaptive"

    def test_set_overrides_defaults(self):
        DynoConfig.set(region="us-east-1", timestamp_format="iso")

        assert DynoConfig.get("region") == "us-east-1"
        assert DynoConfig.get("timestamp_format") == "iso"

    def test_reset_clears_overrides(self):
        DynoConfig.set(region="eu-west-1")
        assert DynoConfig.get("region") == "eu-west-1"

        DynoConfig.reset()
        assert DynoConfig.get("region") == "sa-east-1"

    def test_set_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown configuration key"):
            DynoConfig.set(invalid_key="value")

    def test_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
        DynoConfig.reset()

        assert DynoConfig.get("region") == "ap-southeast-1"

    def test_configure_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
        DynoConfig.set(region="eu-central-1")

        assert DynoConfig.get("region") == "eu-central-1"

    def test_all_returns_resolved_config(self):
        DynoConfig.set(region="us-west-2")
        config = DynoConfig.all()

        assert config["region"] == "us-west-2"
        assert config["timestamp_format"] == "numeric"
        assert "endpoint_url" in config

    def test_env_var_timezone_fallback(self, monkeypatch):
        monkeypatch.setenv("TIMESTAMP_TIMEZONE", "UTC")
        DynoConfig.reset()

        assert DynoConfig.get("timestamp_timezone") == "UTC"


class TestDynoLayerConfigure:
    def test_configure_sets_config(self):
        DynoLayer.configure(region="us-east-1", timestamp_format="iso")

        assert DynoConfig.get("region") == "us-east-1"
        assert DynoConfig.get("timestamp_format") == "iso"

    def test_configure_resets_boto_clients(self):
        CrudMixin._dynamodb = "fake_client"
        CrudMixin._client = "fake_client"

        DynoLayer.configure(region="us-east-1")

        assert CrudMixin._dynamodb is None
        assert CrudMixin._client is None

    def test_configure_unknown_key_raises(self):
        with pytest.raises(ValueError):
            DynoLayer.configure(nonexistent="value")
