from typing import Dict, Tuple, Literal, Union, List

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


def extract_params(*args):
    if len(args) == 2:
        attribute, value = args
        condition = "="
    elif len(args) == 3:
        attribute, condition, value = args
    else:
        raise Exception("'where' method must receive a number of 2 or 3 arguments.")

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
