from decimal import Decimal
from typing import List, Dict, Literal, Any

from dynolayer.crud_mixin import CrudMixin
from dynolayer.utils import extract_params, transform_params_in_query, transform_params_in_filter, Collection


class DynoLayer(CrudMixin):
    def __init__(self, entity="", required_fields=None, fillable=None, timestamps=True):
        super().__init__(entity)

        if fillable is None:
            fillable = []

        if required_fields is None:
            required_fields = []

        self._required_fields = required_fields
        self._timestamps = timestamps
        self._fillable = fillable

        self._index = None
        self._limit = None
        self._project_expression = None
        self._filter_expression = list()
        self._key_condition_expression = list()
        self._force_scan = False

        self._data = {}

    def data(self):
        return self._data

    def fillable(self):
        return self._fillable

    def __getattr__(self, item):
        return self._data.get(item)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    @classmethod
    def all(cls):
        instance = cls()
        response = instance._table.scan()
        data = response["Items"]
        while "LastEvaluatedKey" in response:
            response = instance._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response["Items"])
        # Convert list of dicts to Collection of model instances
        items = []
        for row in data:
            model_instance = cls()
            model_instance._data = row.copy()
            items.append(model_instance)
        return Collection(items)

    @classmethod
    def find(cls, key: dict):
        instance = cls()
        response = instance._table.get_item(
            TableName=instance._entity,
            Key=key
        )

        if not response.get("Item"):
            return None

        for key, value in response["Item"].items():
            instance._data[key] = value

        return instance

    @classmethod
    def where(cls, *args):
        instance = cls()
        instance.and_where(*args)

        return instance

    @classmethod
    def destroy(cls, key: dict):
        instance = cls()
        return instance._delete(key)

    @classmethod
    def create(cls, data: Dict):
        instance = cls()

        for key, value in data.items():
            if key in instance.fillable():
                instance._data[key] = value

        instance.__validate_required_fields()

        if instance._timestamps:
            instance._data["created_at"] = instance._get_current_timestamp()
            instance._data["updated_at"] = instance._get_current_timestamp()

        instance._put(instance.__safe())

        return instance

    def save(self):
        partition_keys = [*self._partition_keys, *self._indexes]
        partition_keys = list(set(partition_keys))
        self.__validate_required_fields(partition_keys)
        keys = {key: self.data()[key] for key in partition_keys}

        if self._timestamps:
            self._data["created_at"] = self._data["created_at"] if self._data.get(
                "created_at") else self._get_current_timestamp()
            self._data["updated_at"] = self._get_current_timestamp()

        return self._update(self.__safe(partition_keys), keys)

    def delete(self):
        keys = {key: self.data()[key] for key in self._partition_keys}
        return self._delete(keys)

    def and_where(self, *args):
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "AND")

        return self

    def where_between(self, attribute: str, start: Any, end: Any):
        self.__set_filter_expression(attribute, "between", [start, end], "AND")
        return self

    def where_in(self, attribute: str, values_in: List[str | int]):
        self.__set_filter_expression(attribute, "in", values_in, "AND")
        return self

    def or_where(self, *args):
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "OR")

        return self

    def where_not(self, *args):
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "AND_NOT")

        return self

    def or_where_not(self, *args):
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "OR_NOT")

        return self

    def limit(self, limit: int):
        self._limit = limit
        return self

    def attributes_to_get(self, project_expression: str | List[str]):
        if isinstance(project_expression, list):
            self._project_expression = ", ".join(project_expression)

        if isinstance(project_expression, str):
            self._project_expression = project_expression

        return self

    def index(self, index: str):
        self._index = index
        return self

    def force_scan(self):
        self._force_scan = True
        return self

    def get(self, return_all=False):
        if not self._filter_expression and not self._key_condition_expression:
            raise Exception("You must specify a filter condition before execute this operation.")

        filter_expression = None
        if self._filter_expression:
            filter_expression = transform_params_in_filter(self._filter_expression)

        items = []
        if self._key_condition_expression and not self._force_scan:
            key_condition = transform_params_in_query(self._key_condition_expression)
            response = self._query(key_condition, filter_expression, self._index, self._limit, return_all, self._project_expression)
            for row in response:
                model_instance = self.__class__()
                model_instance._data = row.copy()
                items.append(model_instance)
        else:
            response = self._scan(filter_expression, self._limit, return_all, self._project_expression)
            for row in response:
                model_instance = self.__class__()
                model_instance._data = row.copy()
                items.append(model_instance)

        self.__reset_query_builder()
        return Collection(items)

    def fetch(self, return_all=False):
        return self.get(return_all)

    @classmethod
    def find_or_fail(cls, key: dict, message="Record not found."):
        """
        Finds a model by key or raises an Exception if not found.
        """
        instance = cls.find(key)
        if instance is None:
            raise Exception(message)
        return instance

    def __validate_required_fields(self, custom_data: List[str] = None):
        if custom_data and len(custom_data) > 0:
            required = custom_data
        else:
            required = self._required_fields

        for field in required:
            if field not in self._data:
                raise Exception(f"Field '{field}' is required but missing.")

    def __safe(self, unset_keys=None):
        data = self._data.copy()

        if unset_keys and isinstance(unset_keys, list):
            for key in unset_keys:
                del data[key]

        for key, value in data.items():
            if isinstance(value, float):
                data[key] = Decimal(str(value))

        return data

    def __set_filter_expression(self, attribute: str, condition: str, value: str | int | List[str | int] | None,
                                filter_operator: Literal["AND", "OR", "AND_NOT", "OR_NOT"]):
        keys = [*self._partition_keys, *self._indexes]
        keys = list(set(keys))
        if attribute in keys:
            self._key_condition_expression.append({attribute: (condition, value)})
        else:
            self._filter_expression.append({filter_operator: {attribute: (condition, value)}})

    def __reset_query_builder(self):
        self._limit = None
        self._key_condition_expression = list()
        self._filter_expression = list()
        self._force_scan = False
