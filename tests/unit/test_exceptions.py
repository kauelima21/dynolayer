import pytest
from dynolayer.exceptions import (
    DynoLayerException,
    QueryException,
    ValidationException,
    RecordNotFoundException,
    InvalidArgumentException,
)


class TestDynoLayerException:
    """Test the base DynoLayerException class"""

    def test_base_exception_with_message_only(self):
        """Test creating base exception with just a message"""
        exc = DynoLayerException("Something went wrong")
        assert "DynoLayer Error: Something went wrong" in str(exc)
        assert exc.message == "Something went wrong"
        assert exc.details == {}

    def test_base_exception_with_details(self):
        """Test creating base exception with details"""
        exc = DynoLayerException(
            "Something went wrong",
            details={"field": "email", "value": "invalid"}
        )
        assert "DynoLayer Error: Something went wrong" in str(exc)
        assert "field: email" in str(exc)
        assert "value: invalid" in str(exc)
        assert exc.details == {"field": "email", "value": "invalid"}

    def test_base_exception_is_catchable(self):
        """Test that base exception can be caught"""
        with pytest.raises(DynoLayerException):
            raise DynoLayerException("Test error")

    def test_child_exceptions_are_catchable_as_base(self):
        """Test that child exceptions can be caught as base exception"""
        with pytest.raises(DynoLayerException):
            raise QueryException("Query error")


class TestQueryException:
    """Test QueryException for query-related errors"""

    def test_query_exception_basic(self):
        """Test basic query exception"""
        exc = QueryException("Missing filter condition")
        assert "DynoLayer Error: Missing filter condition" in str(exc)

    def test_query_exception_with_operation(self):
        """Test query exception with operation specified"""
        exc = QueryException(
            "Missing filter condition",
            operation="get"
        )
        assert "operation: get" in str(exc)

    def test_query_exception_with_suggestions(self):
        """Test query exception with suggestions"""
        exc = QueryException(
            "Missing filter condition",
            operation="get",
            suggestions=["Use .where()", "Use .all()"]
        )
        assert "suggestions: Use .where(), Use .all()" in str(exc)

    def test_query_exception_raised_on_get_without_filter(self, get_user, create_table, aws_mock):
        """Test that QueryException is raised when calling get() without filters"""
        user = get_user()

        with pytest.raises(QueryException) as exc_info:
            user.get()

        assert "filter condition" in str(exc_info.value).lower()
        assert "operation: get" in str(exc_info.value)

    def test_query_exception_raised_on_count_without_filter(self, get_user, create_table, aws_mock):
        """Test that QueryException is raised when calling count() without filters"""
        user = get_user()

        with pytest.raises(QueryException) as exc_info:
            user.count()

        assert "filter condition" in str(exc_info.value).lower()
        assert "operation: count" in str(exc_info.value)


class TestValidationException:
    """Test ValidationException for validation errors"""

    def test_validation_exception_basic(self):
        """Test basic validation exception"""
        exc = ValidationException("Field is required")
        assert "DynoLayer Error: Field is required" in str(exc)

    def test_validation_exception_with_field(self):
        """Test validation exception with field specified"""
        exc = ValidationException(
            "Field is required",
            field="email"
        )
        assert "field: email" in str(exc)

    def test_validation_exception_with_value(self):
        """Test validation exception with value"""
        exc = ValidationException(
            "Invalid value",
            field="email",
            value="invalid.com"
        )
        assert "field: email" in str(exc)
        assert "value: invalid.com" in str(exc)

    def test_validation_exception_with_required_fields(self):
        """Test validation exception with required fields list"""
        exc = ValidationException(
            "Missing required field",
            field="email",
            required_fields=["email", "name", "role"]
        )
        assert "required_fields: email, name, role" in str(exc)

    def test_validation_exception_raised_on_missing_required_field(self, get_user, create_table, aws_mock):
        """Test that ValidationException is raised when required field is missing"""
        with pytest.raises(ValidationException) as exc_info:
            get_user.create({"id": 1})  # Missing required fields: first_name, email, role

        assert "required but missing" in str(exc_info.value).lower()
        assert exc_info.value.details.get("field") is not None

    def test_validation_exception_raised_on_save_without_required_fields(self, get_user, create_table, aws_mock):
        """Test that ValidationException is raised when saving without required fields"""
        user = get_user()
        user.id = 100

        with pytest.raises(ValidationException) as exc_info:
            user.save()

        assert "required but missing" in str(exc_info.value).lower()


class TestRecordNotFoundException:
    """Test RecordNotFoundException for missing records"""

    def test_record_not_found_exception_basic(self):
        """Test basic record not found exception"""
        exc = RecordNotFoundException()
        assert "DynoLayer Error: Record not found" in str(exc)

    def test_record_not_found_exception_with_key(self):
        """Test record not found exception with key"""
        exc = RecordNotFoundException(
            "Record not found",
            key={"id": 999}
        )
        assert "key: {'id': 999}" in str(exc)

    def test_record_not_found_exception_with_entity(self):
        """Test record not found exception with entity"""
        exc = RecordNotFoundException(
            "Record not found",
            entity="User"
        )
        assert "entity: User" in str(exc)

    def test_record_not_found_exception_with_all_details(self):
        """Test record not found exception with all details"""
        exc = RecordNotFoundException(
            "User not found",
            key={"id": 999},
            entity="User"
        )
        assert "User not found" in str(exc)
        assert "key: {'id': 999}" in str(exc)
        assert "entity: User" in str(exc)

    def test_record_not_found_exception_raised_by_find_or_fail(self, get_user, create_table, aws_mock):
        """Test that RecordNotFoundException is raised by find_or_fail when record doesn't exist"""
        with pytest.raises(RecordNotFoundException) as exc_info:
            get_user.find_or_fail({"id": 999})

        assert "Record not found" in str(exc_info.value)
        assert "key:" in str(exc_info.value)
        assert "entity:" in str(exc_info.value)


class TestInvalidArgumentException:
    """Test InvalidArgumentException for invalid arguments"""

    def test_invalid_argument_exception_basic(self):
        """Test basic invalid argument exception"""
        exc = InvalidArgumentException("Invalid argument")
        assert "DynoLayer Error: Invalid argument" in str(exc)

    def test_invalid_argument_exception_with_method(self):
        """Test invalid argument exception with method name"""
        exc = InvalidArgumentException(
            "Invalid argument",
            method="where"
        )
        assert "method: where" in str(exc)

    def test_invalid_argument_exception_with_expected_and_received(self):
        """Test invalid argument exception with expected and received"""
        exc = InvalidArgumentException(
            "Invalid number of arguments",
            method="where",
            expected="2 or 3 arguments",
            received="1 argument"
        )
        assert "method: where" in str(exc)
        assert "expected: 2 or 3 arguments" in str(exc)
        assert "received: 1 argument" in str(exc)

    def test_invalid_argument_exception_raised_on_wrong_args_count(self, get_user, create_table, aws_mock):
        """Test that InvalidArgumentException is raised when wrong number of arguments passed to where()"""
        user = get_user()

        with pytest.raises(InvalidArgumentException) as exc_info:
            user.where("field")  # Missing value

        assert "where" in str(exc_info.value).lower()
        assert "arguments" in str(exc_info.value).lower()

    def test_invalid_argument_exception_raised_on_too_many_args(self, get_user, create_table, aws_mock):
        """Test that InvalidArgumentException is raised with too many arguments"""
        user = get_user()

        with pytest.raises(InvalidArgumentException) as exc_info:
            user.where("field", "=", "value", "extra")

        assert "where" in str(exc_info.value).lower()
        assert "arguments" in str(exc_info.value).lower()


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance"""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from DynoLayerException"""
        assert issubclass(QueryException, DynoLayerException)
        assert issubclass(ValidationException, DynoLayerException)
        assert issubclass(RecordNotFoundException, DynoLayerException)
        assert issubclass(InvalidArgumentException, DynoLayerException)

    def test_all_exceptions_inherit_from_exception(self):
        """Test that all custom exceptions inherit from built-in Exception"""
        assert issubclass(DynoLayerException, Exception)
        assert issubclass(QueryException, Exception)
        assert issubclass(ValidationException, Exception)
        assert issubclass(RecordNotFoundException, Exception)
        assert issubclass(InvalidArgumentException, Exception)

    def test_can_catch_all_with_base_exception(self):
        """Test that all custom exceptions can be caught with base exception"""
        exceptions_to_test = [
            QueryException("test"),
            ValidationException("test"),
            RecordNotFoundException("test"),
            InvalidArgumentException("test"),
        ]

        for exc in exceptions_to_test:
            with pytest.raises(DynoLayerException):
                raise exc

    def test_can_catch_specific_exception_types(self):
        """Test that specific exception types can be caught individually"""
        with pytest.raises(QueryException):
            raise QueryException("test")

        with pytest.raises(ValidationException):
            raise ValidationException("test")

        with pytest.raises(RecordNotFoundException):
            raise RecordNotFoundException("test")

        with pytest.raises(InvalidArgumentException):
            raise InvalidArgumentException("test")


class TestExceptionMessages:
    """Test that exception messages are helpful and informative"""

    def test_query_exception_message_is_helpful(self):
        """Test that QueryException provides helpful error messages"""
        exc = QueryException(
            "Missing filter condition",
            operation="get",
            suggestions=["Use .where() to add a filter", "Use .all() to query all records"]
        )

        error_message = str(exc)
        assert "DynoLayer Error" in error_message
        assert "Missing filter condition" in error_message
        assert "operation: get" in error_message
        assert "suggestions:" in error_message

    def test_validation_exception_message_is_helpful(self):
        """Test that ValidationException provides helpful error messages"""
        exc = ValidationException(
            "Field 'email' is required but missing",
            field="email",
            required_fields=["email", "name", "role"]
        )

        error_message = str(exc)
        assert "DynoLayer Error" in error_message
        assert "email" in error_message
        assert "required_fields:" in error_message

    def test_record_not_found_exception_message_is_helpful(self):
        """Test that RecordNotFoundException provides helpful error messages"""
        exc = RecordNotFoundException(
            "Record not found",
            key={"id": 999},
            entity="User"
        )

        error_message = str(exc)
        assert "DynoLayer Error" in error_message
        assert "Record not found" in error_message
        assert "key:" in error_message
        assert "entity: User" in error_message


if __name__ == "__main__":
    pytest.main()
