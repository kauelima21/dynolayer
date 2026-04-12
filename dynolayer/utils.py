import re
from typing import Any, Dict, Tuple, Literal, Union, List

from boto3.dynamodb.conditions import Attr, Key, ConditionBase


# Collection class for model instances
class Collection:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def count(self):
        return len(self._items)

    def pluck(self, key):
        return [item.data().get(key) for item in self._items]

    def to_list(self):
        return [item.data() for item in self._items]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)


_BETWEEN_RE = re.compile(
    r'(\w+)\s+between\s+:(\w+)\s+and\s+:(\w+)',
    re.IGNORECASE,
)
_BETWEEN_PLACEHOLDER = '\x00BETWEEN\x00'

_CONNECTOR_RE = re.compile(
    r'\s+(AND\s+NOT|OR\s+NOT|AND|OR)\s+',
)

_CONDITION_RE = re.compile(
    r'^(\w+)\s+(=|<>|<=|>=|<|>|begins_with|contains|in|attribute_type)\s+:(\w+)$'
)

_UNARY_RE = re.compile(
    r'^(\w+)\s+(exists|not_exists)$'
)

_CONNECTOR_MAP = {
    'AND': 'AND',
    'OR': 'OR',
    'AND NOT': 'AND_NOT',
    'OR NOT': 'OR_NOT',
}


def parse_expression(expression: str, **values) -> List[Tuple[str, str, str, Any]]:
    from dynolayer.exceptions import InvalidArgumentException

    protected = []
    expr = expression

    for m in _BETWEEN_RE.finditer(expr):
        attr, p1, p2 = m.group(1), m.group(2), m.group(3)
        if p1 not in values:
            raise InvalidArgumentException(
                f"Missing value for placeholder ':{p1}'.",
                method="find",
                expected=f"kwarg '{p1}'",
                received="not provided",
            )
        if p2 not in values:
            raise InvalidArgumentException(
                f"Missing value for placeholder ':{p2}'.",
                method="find",
                expected=f"kwarg '{p2}'",
                received="not provided",
            )
        protected.append((attr, 'between', [values[p1], values[p2]]))
        expr = expr.replace(m.group(0), _BETWEEN_PLACEHOLDER, 1)

    parts = _CONNECTOR_RE.split(expr.strip())

    results: List[Tuple[str, str, str, Any]] = []
    between_idx = 0
    connector = 'AND'

    i = 0
    while i < len(parts):
        fragment = parts[i].strip()
        if not fragment:
            i += 1
            continue

        if fragment.upper() in _CONNECTOR_MAP:
            connector = _CONNECTOR_MAP[fragment.upper()]
            i += 1
            continue

        if _BETWEEN_PLACEHOLDER in fragment:
            results.append((connector, *protected[between_idx]))
            between_idx += 1
            connector = 'AND'
            i += 1
            continue

        unary_match = _UNARY_RE.match(fragment)
        if unary_match:
            attr = unary_match.group(1)
            op = unary_match.group(2)
            results.append((connector, attr, op, None))
            connector = 'AND'
            i += 1
            continue

        cond_match = _CONDITION_RE.match(fragment)
        if cond_match:
            attr = cond_match.group(1)
            op = cond_match.group(2)
            placeholder = cond_match.group(3)
            if placeholder not in values:
                raise InvalidArgumentException(
                    f"Missing value for placeholder ':{placeholder}'.",
                    method="find",
                    expected=f"kwarg '{placeholder}'",
                    received="not provided",
                )
            val = values[placeholder]
            if op == 'in' and not isinstance(val, list):
                raise InvalidArgumentException(
                    f"Operator 'in' requires a list value for ':{placeholder}'.",
                    method="find",
                    expected="list",
                    received=type(val).__name__,
                )
            results.append((connector, attr, op, val))
            connector = 'AND'
            i += 1
            continue

        raise InvalidArgumentException(
            f"Invalid expression syntax: '{fragment}'.",
            method="find",
            expected="'attribute operator :placeholder' or 'attribute exists/not_exists'",
            received=fragment,
        )

    if not results:
        raise InvalidArgumentException(
            "Empty or invalid expression.",
            method="find",
        )

    return results


def extract_params(*args):
    from dynolayer.exceptions import InvalidArgumentException

    if len(args) == 2:
        attribute, value = args
        condition = "="
    elif len(args) == 3:
        attribute, condition, value = args
    else:
        raise InvalidArgumentException(
            "'where' method must receive 2 or 3 arguments.",
            method="where",
            expected="2 or 3 arguments (attribute, [condition,] value)",
            received=f"{len(args)} arguments"
        )

    return attribute, condition, value


def extract_query_attributes(query: Dict[str, Tuple[str, Union[str, int]]]):
    attribute, attr_value = next(iter(query.items()))
    condition, value = attr_value

    return attribute, condition, value


def get_logical_expression(
        attr: str,
        value: str | int | List[str | int] | None,
        operator: str,
        mode: Literal["key_condition", "filter"]
) -> ConditionBase:
    attribute = Attr
    if mode == "key_condition":
        attribute = Key

    operators_map = {
        "=": attribute(attr).eq(value),
        "<": attribute(attr).lt(value),
        "<=": attribute(attr).lte(value),
        ">": attribute(attr).gt(value),
        ">=": attribute(attr).gte(value),
        "begins_with": attribute(attr).begins_with(value),
    }

    if isinstance(value, list):
        operators_map["between"] = attribute(attr).between(value[0], value[1])

    if mode == "filter":
        operators_map["<>"] = attribute(attr).ne(value)
        operators_map["contains"] = attribute(attr).contains(value)
        operators_map["in"] = attribute(attr).is_in(value)
        operators_map["exists"] = attribute(attr).exists()
        operators_map["not_exists"] = attribute(attr).not_exists()
        operators_map["attribute_type"] = attribute(attr).attribute_type(value)

    return operators_map[operator]


def transform_params_in_query(expressions: List[Dict[str, Tuple[str, Union[str, int]]]]):
    final_query = None
    for expression in expressions:
        attr, condition, attr_value = extract_query_attributes(expression)
        response = get_logical_expression(attr, attr_value, condition, "key_condition")

        if not final_query:
            final_query = response
        else:
            final_query = final_query & response

    return final_query


def transform_params_in_filter(expressions: List[Dict[str, Dict[str, Tuple[str, Union[str, int]]]]]):
    final_filter = None
    filters_by_condition: List[Tuple[str, ConditionBase]] = []

    for expression in expressions:
        for key, value in expression.items():
            attr, condition, attr_value = extract_query_attributes(value)
            response = get_logical_expression(attr, attr_value, condition, "filter")

            filters_by_condition.append((key, response))

    for item in filters_by_condition:
        condition, filter_expression = item
        if not final_filter and condition in ["AND", "OR"]:
            final_filter = filter_expression
            continue
        elif not final_filter and condition in ["AND_NOT", "OR_NOT"]:
            final_filter = ~filter_expression
            continue

        if condition == "AND":
            final_filter = final_filter & filter_expression
        elif condition == "OR":
            final_filter = final_filter | filter_expression
        elif condition == "AND_NOT":
            final_filter = final_filter & ~filter_expression
        elif condition == "OR_NOT":
            final_filter = final_filter | ~filter_expression

    return final_filter
