"""
Custom exceptions for DynoLayer.

These exceptions provide more context and better error messages to help developers
debug issues when working with DynamoDB through DynoLayer.
"""


class DynoLayerException(Exception):
    """
    Base exception class for all DynoLayer exceptions.

    All custom DynoLayer exceptions inherit from this class,
    making it easy to catch any DynoLayer-specific error.
    """

    def __init__(self, message, details=None):
        """
        Initialize the exception.

        Args:
            message (str): The error message
            details (dict, optional): Additional context about the error
        """
        self.message = message
        self.details = details or {}

        # Build detailed error message
        error_parts = [f"DynoLayer Error: {message}"]

        if self.details:
            error_parts.append("\nDetails:")
            for key, value in self.details.items():
                error_parts.append(f"  - {key}: {value}")

        super().__init__("".join(error_parts))


class QueryException(DynoLayerException):
    """
    Exception raised for query-related errors.

    This exception is raised when there are issues with building or executing queries,
    such as missing filter conditions or invalid query parameters.

    Example:
        >>> User.where("role", "admin").get()
        QueryException: You must specify a filter condition before executing this operation.
    """

    def __init__(self, message, operation=None, suggestions=None):
        """
        Initialize the query exception.

        Args:
            message (str): The error message
            operation (str, optional): The operation that failed (e.g., 'get', 'fetch', 'count')
            suggestions (list, optional): Suggested fixes for the error
        """
        details = {}
        if operation:
            details['operation'] = operation
        if suggestions:
            details['suggestions'] = ', '.join(suggestions)

        super().__init__(message, details)


class ValidationException(DynoLayerException):
    """
    Exception raised for validation errors.

    This exception is raised when data validation fails, such as missing required fields
    or invalid field values.

    Example:
        >>> User.create({"id": 1})
        ValidationException: Field 'email' is required but missing.
    """

    def __init__(self, message, field=None, value=None, required_fields=None):
        """
        Initialize the validation exception.

        Args:
            message (str): The error message
            field (str, optional): The field that failed validation
            value (any, optional): The invalid value
            required_fields (list, optional): List of required fields
        """
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
        if required_fields:
            details['required_fields'] = ', '.join(required_fields)

        super().__init__(message, details)


class RecordNotFoundException(DynoLayerException):
    """
    Exception raised when a record is not found.

    This exception is raised by find_or_fail() when a record cannot be found
    with the specified key.

    Example:
        >>> User.find_or_fail({"id": 999})
        RecordNotFoundException: Record not found.
    """

    def __init__(self, message="Record not found", key=None, entity=None):
        """
        Initialize the record not found exception.

        Args:
            message (str): The error message
            key (dict, optional): The key used to search for the record
            entity (str, optional): The entity/table name
        """
        details = {}
        if key:
            details['key'] = str(key)
        if entity:
            details['entity'] = entity

        super().__init__(message, details)


class InvalidArgumentException(DynoLayerException):
    """
    Exception raised for invalid arguments.

    This exception is raised when a method receives invalid arguments,
    such as incorrect number of parameters or wrong types.

    Example:
        >>> User.where("field")
        InvalidArgumentException: 'where' method must receive 2 or 3 arguments.
    """

    def __init__(self, message, method=None, expected=None, received=None):
        """
        Initialize the invalid argument exception.

        Args:
            message (str): The error message
            method (str, optional): The method name
            expected (str, optional): Expected argument format
            received (str, optional): What was actually received
        """
        details = {}
        if method:
            details['method'] = method
        if expected:
            details['expected'] = expected
        if received:
            details['received'] = str(received)

        super().__init__(message, details)
