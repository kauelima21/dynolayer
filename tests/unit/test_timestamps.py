import pytest

from dynolayer.config import DynoConfig


class TestTimestampNumeric:
    def test_create_adds_numeric_timestamps(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert isinstance(user.created_at, int)
        assert isinstance(user.updated_at, int)

    def test_save_updates_numeric_timestamp(self, get_user, create_table, aws_mock):
        user = get_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        original_created = user.created_at
        user.first_name = "Jane"
        user.save()

        assert user.created_at == original_created
        assert isinstance(user.updated_at, int)


class TestTimestampIso:
    def test_create_adds_iso_timestamps_via_configure(self, get_user, create_table, aws_mock):
        DynoLayer.configure(timestamp_format="iso")

        user = get_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert isinstance(user.created_at, str)
        assert "T" in user.created_at  # ISO 8601 format

    def test_create_with_model_override(self, create_table, aws_mock):
        from dynolayer.dynolayer import DynoLayer

        class IsoUser(DynoLayer):
            def __init__(self):
                super().__init__(
                    entity="users",
                    required_fields=["first_name", "email", "role"],
                    fillable=["id", "first_name", "email", "role"],
                    timestamps=True,
                    timestamp_format="iso",
                )

        user = IsoUser.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert isinstance(user.created_at, str)
        assert "T" in user.created_at

    def test_model_override_takes_priority_over_global(self, create_table, aws_mock):
        from dynolayer.dynolayer import DynoLayer

        DynoLayer.configure(timestamp_format="numeric")

        class IsoUser(DynoLayer):
            def __init__(self):
                super().__init__(
                    entity="users",
                    required_fields=["first_name", "email", "role"],
                    fillable=["id", "first_name", "email", "role"],
                    timestamps=True,
                    timestamp_format="iso",
                )

        user = IsoUser.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert isinstance(user.created_at, str)
        assert "T" in user.created_at

    def test_global_numeric_stays_numeric(self, get_user, create_table, aws_mock):
        DynoLayer.configure(timestamp_format="numeric")

        user = get_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert isinstance(user.created_at, int)


class TestTimestampTimezone:
    def test_configure_timezone(self, get_user, create_table, aws_mock):
        DynoLayer.configure(timestamp_timezone="UTC", timestamp_format="iso")

        user = get_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })

        assert "+00:00" in user.created_at or "Z" in user.created_at


# Need DynoLayer import at module level for configure calls
from dynolayer.dynolayer import DynoLayer
