import pytest

from dynolayer.exceptions import (
    ValidationException, QueryException, RecordNotFoundException,
)


class TestSilentModeClassMethods:
    def test_find_with_invalid_key_raises_by_default(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException):
            get_user.find({})

    def test_find_with_invalid_key_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.find({})
        assert result is None
        error = get_silent_user.fail()
        assert isinstance(error, ValidationException)

    def test_create_missing_required_fields_raises_by_default(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException):
            get_user.create({"id": 1})

    def test_create_missing_required_fields_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.create({"id": 1})
        assert result is None
        error = get_silent_user.fail()
        assert isinstance(error, ValidationException)

    def test_delete_with_invalid_key_raises_by_default(self, get_user, create_table, aws_mock):
        with pytest.raises(ValidationException):
            get_user.delete({})

    def test_delete_with_invalid_key_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.delete({})
        assert result is False
        assert isinstance(get_silent_user.fail(), ValidationException)

    def test_find_or_fail_not_found_raises_by_default(self, get_user, create_table, aws_mock):
        with pytest.raises(RecordNotFoundException):
            get_user.find_or_fail({"id": 999})

    def test_find_or_fail_not_found_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.find_or_fail({"id": 999})
        assert result is None
        assert isinstance(get_silent_user.fail(), RecordNotFoundException)

    def test_batch_create_missing_required_fields_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.batch_create([{"id": 1}])
        assert result == []
        assert isinstance(get_silent_user.fail(), ValidationException)

    def test_batch_destroy_invalid_key_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.batch_destroy([{}])
        assert result is False
        assert isinstance(get_silent_user.fail(), ValidationException)

    def test_batch_find_invalid_key_silent(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.batch_find([{}])
        assert len(result) == 0
        assert isinstance(get_silent_user.fail(), ValidationException)


class TestSilentModeInstanceMethods:
    def test_save_missing_required_field_raises_by_default(self, get_user, create_table, aws_mock):
        user = get_user()
        user.id = 1
        with pytest.raises(ValidationException):
            user.save()

    def test_save_missing_required_field_silent(self, get_silent_user, create_table, aws_mock):
        user = get_silent_user()
        user.id = 1
        result = user.save()
        assert result is False
        assert isinstance(user.fail(), ValidationException)

    def test_get_without_filter_raises_by_default(self, get_user, create_table, aws_mock):
        user = get_user()
        with pytest.raises(QueryException):
            user.get()

    def test_get_without_filter_silent(self, get_silent_user, create_table, aws_mock):
        user = get_silent_user()
        result = user.get()
        assert len(result) == 0
        assert isinstance(user.fail(), QueryException)

    def test_count_without_filter_raises_by_default(self, get_user, create_table, aws_mock):
        user = get_user()
        with pytest.raises(QueryException):
            user.count()

    def test_count_without_filter_silent(self, get_silent_user, create_table, aws_mock):
        user = get_silent_user()
        result = user.count()
        assert result == 0
        assert isinstance(user.fail(), QueryException)


class TestSilentModeErrorReset:
    def test_fail_resets_on_successful_operation(self, get_silent_user, create_table, aws_mock):
        # First: trigger an error
        get_silent_user.find({})
        assert get_silent_user.fail() is not None

        # Second: successful operation resets the error
        get_silent_user.find({"id": 1})
        assert get_silent_user.fail() is None

    def test_instance_fail_resets_on_successful_operation(self, get_silent_user, create_table, aws_mock):
        user = get_silent_user()
        user.id = 1

        # First: trigger an error (missing required fields)
        user.save()
        assert user.fail() is not None

        # Second: successful operation resets the error
        user.first_name = "John"
        user.email = "john@mail.com"
        user.role = "admin"
        user.save()
        assert user.fail() is None


class TestSilentModeSuccessfulOperations:
    def test_create_succeeds_in_silent_mode(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.create({
            "id": 1,
            "first_name": "John",
            "email": "john@mail.com",
            "role": "admin",
        })
        assert result is not None
        assert result.id == 1
        assert get_silent_user.fail() is None

    def test_save_succeeds_in_silent_mode(self, get_silent_user, create_table, aws_mock):
        user = get_silent_user()
        user.id = 1
        user.first_name = "John"
        user.email = "john@mail.com"
        user.role = "admin"
        assert user.save() is True
        assert user.fail() is None

    def test_find_returns_none_for_missing_record_no_error(self, get_silent_user, create_table, aws_mock):
        result = get_silent_user.find({"id": 999})
        assert result is None
        assert get_silent_user.fail() is None


if __name__ == "__main__":
    pytest.main()
