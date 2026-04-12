import pytest
from dynolayer.utils import parse_expression
from dynolayer.exceptions import InvalidArgumentException


class TestParseExpressionBasicOperators:
    def test_equal(self):
        result = parse_expression("user_id = :uid", uid="123")
        assert result == [("AND", "user_id", "=", "123")]

    def test_less_than(self):
        result = parse_expression("age < :max", max=30)
        assert result == [("AND", "age", "<", 30)]

    def test_less_than_or_equal(self):
        result = parse_expression("age <= :max", max=30)
        assert result == [("AND", "age", "<=", 30)]

    def test_greater_than(self):
        result = parse_expression("age > :min", min=18)
        assert result == [("AND", "age", ">", 18)]

    def test_greater_than_or_equal(self):
        result = parse_expression("age >= :min", min=18)
        assert result == [("AND", "age", ">=", 18)]

    def test_not_equal(self):
        result = parse_expression("status <> :s", s="deleted")
        assert result == [("AND", "status", "<>", "deleted")]

    def test_begins_with(self):
        result = parse_expression("name begins_with :prefix", prefix="Jo")
        assert result == [("AND", "name", "begins_with", "Jo")]

    def test_contains(self):
        result = parse_expression("tags contains :tag", tag="python")
        assert result == [("AND", "tags", "contains", "python")]

    def test_in_operator(self):
        result = parse_expression("status in :list", list=["active", "pending"])
        assert result == [("AND", "status", "in", ["active", "pending"])]

    def test_attribute_type(self):
        result = parse_expression("data attribute_type :t", t="S")
        assert result == [("AND", "data", "attribute_type", "S")]


class TestParseExpressionBetween:
    def test_between(self):
        result = parse_expression("age between :min and :max", min=18, max=65)
        assert result == [("AND", "age", "between", [18, 65])]

    def test_between_with_strings(self):
        result = parse_expression(
            "created_at between :start and :end",
            start="2024-01-01",
            end="2024-12-31",
        )
        assert result == [("AND", "created_at", "between", ["2024-01-01", "2024-12-31"])]


class TestParseExpressionUnary:
    def test_exists(self):
        result = parse_expression("email exists")
        assert result == [("AND", "email", "exists", None)]

    def test_not_exists(self):
        result = parse_expression("phone not_exists")
        assert result == [("AND", "phone", "not_exists", None)]


class TestParseExpressionConnectors:
    def test_and_connector(self):
        result = parse_expression("user_id = :uid AND status = :s", uid="123", s="active")
        assert result == [
            ("AND", "user_id", "=", "123"),
            ("AND", "status", "=", "active"),
        ]

    def test_or_connector(self):
        result = parse_expression("city = :c1 OR city = :c2", c1="SP", c2="RJ")
        assert result == [
            ("AND", "city", "=", "SP"),
            ("OR", "city", "=", "RJ"),
        ]

    def test_and_not_connector(self):
        result = parse_expression("user_id = :uid AND NOT status = :s", uid="123", s="deleted")
        assert result == [
            ("AND", "user_id", "=", "123"),
            ("AND_NOT", "status", "=", "deleted"),
        ]

    def test_or_not_connector(self):
        result = parse_expression("user_id = :uid OR NOT archived = :a", uid="123", a=True)
        assert result == [
            ("AND", "user_id", "=", "123"),
            ("OR_NOT", "archived", "=", True),
        ]


class TestParseExpressionComplex:
    def test_multiple_conditions(self):
        result = parse_expression(
            "user_id = :uid AND email exists AND NOT status = :s",
            uid="123",
            s="deleted",
        )
        assert result == [
            ("AND", "user_id", "=", "123"),
            ("AND", "email", "exists", None),
            ("AND_NOT", "status", "=", "deleted"),
        ]

    def test_between_with_and_connector(self):
        result = parse_expression(
            "user_id = :uid AND created_at between :start and :end",
            uid="123",
            start="2024-01-01",
            end="2024-12-31",
        )
        assert result == [
            ("AND", "user_id", "=", "123"),
            ("AND", "created_at", "between", ["2024-01-01", "2024-12-31"]),
        ]


class TestParseExpressionErrors:
    def test_missing_placeholder_value(self):
        with pytest.raises(InvalidArgumentException, match="Missing value for placeholder"):
            parse_expression("user_id = :uid")

    def test_invalid_syntax(self):
        with pytest.raises(InvalidArgumentException, match="Invalid expression syntax"):
            parse_expression("invalid expression here", val="x")

    def test_in_with_non_list_value(self):
        with pytest.raises(InvalidArgumentException, match="requires a list"):
            parse_expression("status in :s", s="active")

    def test_empty_expression(self):
        with pytest.raises(InvalidArgumentException, match="Empty or invalid"):
            parse_expression("")

    def test_between_missing_start_value(self):
        with pytest.raises(InvalidArgumentException, match="Missing value for placeholder"):
            parse_expression("age between :min and :max", max=65)

    def test_between_missing_end_value(self):
        with pytest.raises(InvalidArgumentException, match="Missing value for placeholder"):
            parse_expression("age between :min and :max", min=18)


if __name__ == "__main__":
    pytest.main()
