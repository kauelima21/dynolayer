from __future__ import annotations

import re
import uuid
import warnings
from decimal import Decimal
from typing import List, Dict, Literal, Any, Optional

from boto3.dynamodb.conditions import Attr

from dynolayer.config import DynoConfig
from dynolayer.crud_mixin import CrudMixin
from dynolayer.exceptions import (
    DynoLayerException, QueryException, ValidationException, RecordNotFoundException,
    InvalidArgumentException, AutoIdException, )
from dynolayer.utils import extract_params, parse_expression, transform_params_in_query, transform_params_in_filter, Collection


class _HybridWhere:
    def __get__(self, obj, cls):
        if obj is None:
            def class_where(*args):
                instance = cls()
                instance.and_where(*args)
                return instance
            return class_where
        return obj.and_where


class _HybridFail:
    def __get__(self, obj, cls):
        if obj is None:
            def class_fail():
                return cls._class_last_error
            return class_fail

        def instance_fail():
            return obj._last_error
        return instance_fail


class DynoLayer(CrudMixin):
    _VALID_AUTO_ID_STRATEGIES = ("uuid4", "uuid1", "uuid7", "numeric")
    raise_on_error = False
    _class_last_error = None

    def __init__(self, entity="", required_fields=None, partition_key: str = "id", timestamps=True,
                 fillable=None, timestamp_format: Literal["numeric", "iso"] = "iso",
                 auto_id: Literal["uuid4", "uuid1", "uuid7", "numeric"] = None,
                 auto_id_length=None, auto_id_table=None, sort_key: str = None):
        if auto_id is not None:
            if auto_id not in self._VALID_AUTO_ID_STRATEGIES:
                raise InvalidArgumentException(
                    f"Invalid auto_id strategy: '{auto_id}'",
                    method="__init__",
                    expected=f"One of: {', '.join(self._VALID_AUTO_ID_STRATEGIES)}",
                    received=auto_id
                )
            if auto_id_length is not None:
                if auto_id == "numeric":
                    raise InvalidArgumentException(
                        "auto_id_length is not supported with 'numeric' strategy.",
                        method="__init__"
                    )
                if not isinstance(auto_id_length, int) or auto_id_length < 16 or auto_id_length > 32:
                    raise InvalidArgumentException(
                        "auto_id_length must be an integer between 16 and 32.",
                        method="__init__",
                        expected="integer between 16 and 32",
                        received=str(auto_id_length)
                    )

        super().__init__(entity, partition_key=partition_key, sort_key=sort_key)

        if fillable is None:
            fillable = []

        if required_fields is None:
            required_fields = []

        self._required_fields = required_fields
        self._timestamps = timestamps
        self._timestamp_format = timestamp_format
        self._fillable = fillable
        self._auto_id = auto_id
        self._auto_id_length = auto_id_length
        self._auto_id_table = auto_id_table
        self._all_index_keys = {key for idx in self._indexes.values() for key in idx["keys"]}

        self._index = None
        self._limit = None
        self._project_expression = None
        self._filter_expression = list()
        self._key_condition_expression = list()
        self._force_scan = False
        self._offset = None
        self._scan_all = False

        self._data = {}

        # Error tracking for silent mode
        self._last_error = None

        # Pagination metadata
        self._last_evaluated_key = None
        self._get_count = 0

    def data(self) -> Dict:
        return self._data

    def fillable(self) -> List[str]:
        return self._fillable

    def last_evaluated_key(self) -> Optional[Dict]:
        return self._last_evaluated_key

    def get_count(self) -> int:
        return self._get_count

    def __getattr__(self, item):
        return self._data.get(item)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def __delitem__(self, key):
        del self._data[key]

    @classmethod
    def configure(cls, **kwargs) -> None:
        DynoConfig.set(**kwargs)
        cls._reset_boto_clients()

    @classmethod
    def all(cls) -> DynoLayer:
        instance = cls()
        instance._scan_all = True
        return instance

    @classmethod
    def get_item(cls, key: dict, attributes: List[str] = None) -> Optional[DynoLayer]:
        cls._class_last_error = None
        try:
            instance = cls()
            instance.__validate_key_dict(key)

            kwargs = {"TableName": instance._entity, "Key": key}
            if attributes:
                attr_names = {f"#proj_{i}": attr for i, attr in enumerate(attributes)}
                kwargs["ProjectionExpression"] = ", ".join(attr_names.keys())
                kwargs["ExpressionAttributeNames"] = attr_names

            response = instance._table.get_item(**kwargs)

            if not response.get("Item"):
                return None

            for key, value in response["Item"].items():
                instance._data[key] = value

            return instance
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return None

    def find(self, terms: str = None, /, **values) -> DynoLayer:
        if terms is None:
            self._scan_all = True
            return self

        parsed = parse_expression(terms, **values)
        for connector, attribute, condition, value in parsed:
            self.__set_filter_expression(attribute, condition, value, connector)

        return self

    where = _HybridWhere()
    fail = _HybridFail()

    @classmethod
    def delete(cls, key: dict) -> bool:
        cls._class_last_error = None
        try:
            instance = cls()
            instance.__validate_key_dict(key)
            return instance._delete(key)
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return False

    @classmethod
    def create(cls, data: Dict, unique=False) -> Optional[DynoLayer]:
        cls._class_last_error = None
        try:
            instance = cls()

            for key, value in data.items():
                if key in instance.fillable():
                    instance._data[key] = value

            instance.__validate_required_fields()
            instance.__apply_auto_id()

            if instance._timestamps:
                instance._data["created_at"] = instance._get_current_timestamp(instance._timestamp_format)
                instance._data["updated_at"] = instance._get_current_timestamp(instance._timestamp_format)

            condition = Attr(instance._hash_key).not_exists() if unique else None
            instance._put(instance.__safe(), condition=condition)

            return instance
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return None

    @classmethod
    def batch_create(cls, items: List[Dict]) -> List[DynoLayer]:
        cls._class_last_error = None
        try:
            ref_instance = cls()
            instances = []

            for data in items:
                instance = cls()

                for key, value in data.items():
                    if key in instance.fillable():
                        instance._data[key] = value

                instance.__validate_required_fields()
                instances.append(instance)

            # Pre-generate numeric IDs in a single atomic call
            numeric_ids = None
            if ref_instance._auto_id == "numeric":
                pk_field = ref_instance._partition_keys[0]
                items_needing_id = [
                    pk_field not in inst._data or inst._data.get(pk_field) is None
                    for inst in instances
                ]
                count = sum(items_needing_id)
                if count > 0:
                    numeric_ids = ref_instance.__generate_numeric_id_batch(count)

            numeric_id_index = 0
            for instance in instances:
                if numeric_ids is not None:
                    pk_field = instance._partition_keys[0]
                    if pk_field not in instance._data or instance._data.get(pk_field) is None:
                        instance._data[pk_field] = numeric_ids[numeric_id_index]
                        numeric_id_index += 1
                else:
                    instance.__apply_auto_id()

                if instance._timestamps:
                    instance._data["created_at"] = instance._get_current_timestamp(instance._timestamp_format)
                    instance._data["updated_at"] = instance._get_current_timestamp(instance._timestamp_format)

            safe_items = [inst.__safe() for inst in instances]
            cls()._batch_put(safe_items)

            return instances
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return []

    @classmethod
    def batch_find(cls, keys: List[Dict]) -> Collection:
        cls._class_last_error = None
        try:
            instance = cls()
            for key in keys:
                instance.__validate_key_dict(key)
            raw_items = instance._batch_get(keys)

            items = []
            for row in raw_items:
                model_instance = cls()
                model_instance._data = row.copy()
                items.append(model_instance)

            return Collection(items)
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return Collection([])

    @classmethod
    def batch_destroy(cls, keys: List[Dict]) -> bool:
        cls._class_last_error = None
        try:
            instance = cls()
            for key in keys:
                instance.__validate_key_dict(key)
            return instance._batch_delete(keys)
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return False

    @classmethod
    def prepare_put(cls, data: Dict) -> Dict:
        instance = cls()

        for key, value in data.items():
            if key in instance.fillable():
                instance._data[key] = value

        instance.__apply_auto_id()

        if instance._timestamps:
            instance._data["created_at"] = instance._get_current_timestamp(instance._timestamp_format)
            instance._data["updated_at"] = instance._get_current_timestamp(instance._timestamp_format)

        return {"Put": {"TableName": instance._entity, "Item": instance.__safe()}}

    @classmethod
    def prepare_delete(cls, key: dict) -> Dict:
        instance = cls()
        instance.__validate_key_dict(key)
        return {"Delete": {"TableName": instance._entity, "Key": key}}

    @classmethod
    def prepare_update(cls, key: dict, data: Dict) -> Dict:
        instance = cls()
        instance.__validate_key_dict(key)

        expression_values = {}
        expression_names = {}
        update_parts = []

        for i, (k, value) in enumerate(data.items()):
            if isinstance(value, float):
                value = Decimal(str(value))
            safe = re.sub(r"[^a-zA-Z0-9_]", "_", k) + f"_{i}"
            expression_values[f":{safe}"] = value
            expression_names[f"#{safe}"] = k
            update_parts.append(f"#{safe} = :{safe}")

        return {"Update": {
            "TableName": instance._entity,
            "Key": key,
            "UpdateExpression": "SET " + ", ".join(update_parts),
            "ExpressionAttributeValues": expression_values,
            "ExpressionAttributeNames": expression_names,
        }}

    @staticmethod
    def transact_write(operations: List[Dict]) -> bool:
        from boto3.dynamodb.types import TypeSerializer
        from dynolayer.crud_mixin import CrudMixin

        serializer = TypeSerializer()
        serialized_ops = []

        for op in operations:
            serialized_op = {}
            for op_type, params in op.items():
                serialized_params = dict(params)
                if "Item" in serialized_params:
                    serialized_params["Item"] = {
                        k: serializer.serialize(v) for k, v in serialized_params["Item"].items()
                    }
                if "Key" in serialized_params:
                    serialized_params["Key"] = {
                        k: serializer.serialize(v) for k, v in serialized_params["Key"].items()
                    }
                if "ExpressionAttributeValues" in serialized_params:
                    serialized_params["ExpressionAttributeValues"] = {
                        k: serializer.serialize(v) for k, v in serialized_params["ExpressionAttributeValues"].items()
                    }
                serialized_op[op_type] = serialized_params
            serialized_ops.append(serialized_op)

        client = CrudMixin._get_client()
        client.transact_write_items(TransactItems=serialized_ops)
        return True

    @staticmethod
    def transact_get(requests: List[tuple]) -> List[Optional[DynoLayer]]:
        from boto3.dynamodb.types import TypeSerializer, TypeDeserializer
        from dynolayer.crud_mixin import CrudMixin

        serializer = TypeSerializer()
        deserializer = TypeDeserializer()
        order = []
        transact_items = []

        for model_cls, key in requests:
            instance = model_cls()
            instance._DynoLayer__validate_key_dict(key)
            serialized_key = {k: serializer.serialize(v) for k, v in key.items()}
            transact_items.append({"Get": {"TableName": instance._entity, "Key": serialized_key}})
            order.append(model_cls)

        client = CrudMixin._get_client()
        response = client.transact_get_items(TransactItems=transact_items)

        items = []
        for i, resp in enumerate(response.get("Responses", [])):
            raw = resp.get("Item")
            if raw:
                deserialized = {k: deserializer.deserialize(v) for k, v in raw.items()}
                model_instance = order[i]()
                model_instance._data = deserialized
                items.append(model_instance)
            else:
                items.append(None)

        return items

    def save(self, condition=None) -> bool:
        self._last_error = None
        try:
            self.__validate_required_fields()
            self.__apply_auto_id()
            self.__validate_required_fields(self._partition_keys)
            keys = {key: self.data()[key] for key in self._partition_keys}

            if self._timestamps:
                self._data["created_at"] = self._data["created_at"] if self._data.get(
                    "created_at") else self._get_current_timestamp(self._timestamp_format)
                self._data["updated_at"] = self._get_current_timestamp(self._timestamp_format)

            return self._update(self.__safe(self._partition_keys), keys, condition=condition)
        except DynoLayerException as e:
            if self.raise_on_error:
                raise
            self._last_error = e
            return False

    def destroy(self) -> bool:
        self._last_error = None
        try:
            keys = {key: self.data()[key] for key in self._partition_keys}
            return self._delete(keys)
        except DynoLayerException as e:
            if self.raise_on_error:
                raise
            self._last_error = e
            return False

    def and_where(self, *args) -> DynoLayer:
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "AND")

        return self

    def where_between(self, attribute: str, start: Any, end: Any) -> DynoLayer:
        self.__set_filter_expression(attribute, "between", [start, end], "AND")
        return self

    def where_in(self, attribute: str, values_in: List[str | int]) -> DynoLayer:
        self.__set_filter_expression(attribute, "in", values_in, "AND")
        return self

    def or_where(self, *args) -> DynoLayer:
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "OR")

        return self

    def where_not(self, *args) -> DynoLayer:
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "AND_NOT")

        return self

    def or_where_not(self, *args) -> DynoLayer:
        attribute, condition, value = extract_params(*args)
        self.__set_filter_expression(attribute, condition, value, "OR_NOT")

        return self

    def limit(self, limit: int) -> DynoLayer:
        self._limit = limit
        return self

    def attributes_to_get(self, project_expression: str | List[str]) -> DynoLayer:
        if isinstance(project_expression, list):
            self._project_expression = ", ".join(project_expression)

        if isinstance(project_expression, str):
            self._project_expression = project_expression

        return self

    def index(self, index: str) -> DynoLayer:
        self._index = index
        if not self._indexes:
            self._load_indexes()
        return self

    def force_scan(self) -> DynoLayer:
        self._force_scan = True
        return self

    def offset(self, last_evaluated_key: dict) -> DynoLayer:
        self._offset = last_evaluated_key
        return self

    def get(self, all=False, paginate=False) -> Collection | DynoLayer | None:
        self._last_error = None
        try:
            if not self._scan_all and not self._filter_expression and not self._key_condition_expression:
                raise QueryException(
                    "You must specify a filter condition before executing this operation.",
                    operation="get",
                    suggestions=[
                        "Use .where() to add a filter condition",
                        "Use .all() to query all records"
                    ]
                )

            self.__resolve_key_conditions()
            self.__validate_index()

            filter_expression = None
            if self._filter_expression:
                filter_expression = transform_params_in_filter(self._filter_expression)

            items = []
            if self._key_condition_expression and not self._force_scan and not self._scan_all:
                key_condition = transform_params_in_query(self._key_condition_expression)
                response = self._query(key_condition, filter_expression, self._index, self._limit, paginate, self._project_expression, self._offset)
                for row in response["Items"]:
                    model_instance = self.__class__()
                    model_instance._data = row.copy()
                    items.append(model_instance)
            else:
                response = self._scan(filter_expression, self._limit, paginate, self._project_expression, self._offset)
                for row in response["Items"]:
                    model_instance = self.__class__()
                    model_instance._data = row.copy()
                    items.append(model_instance)

            # Store pagination metadata BEFORE reset
            last_key = response.get("LastEvaluatedKey")
            count = response.get("Count", len(items))

            self.__reset_query_builder()

            # Set pagination metadata AFTER reset
            self._last_evaluated_key = last_key
            self._get_count = count

            if not all:
                return Collection(items).first()

            return Collection(items)
        except DynoLayerException as e:
            if self.raise_on_error:
                raise
            self._last_error = e
            self.__reset_query_builder()
            return Collection([])

    def fetch(self, all=False, paginate=False) -> Collection | DynoLayer | None:
        return self.get(all, paginate)

    def stream(self):
        self.__resolve_key_conditions()
        self.__validate_index()

        filter_expression = None
        if self._filter_expression:
            filter_expression = transform_params_in_filter(self._filter_expression)

        use_query = self._key_condition_expression and not self._force_scan and not self._scan_all

        if use_query:
            key_condition = transform_params_in_query(self._key_condition_expression)
            kwargs = {"KeyConditionExpression": key_condition}
            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if self._index:
                kwargs["IndexName"] = self._index
            if self._project_expression:
                kwargs["ProjectionExpression"] = self._project_expression
            op = self._table.query
        else:
            kwargs = {}
            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if self._project_expression:
                kwargs["ProjectionExpression"] = self._project_expression
            op = self._table.scan

        self.__reset_query_builder()

        while True:
            response = op(**kwargs)
            for row in response["Items"]:
                model_instance = self.__class__()
                model_instance._data = row.copy()
                yield model_instance
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    def count(self) -> int:
        self._last_error = None
        try:
            if not self._scan_all and not self._filter_expression and not self._key_condition_expression:
                raise QueryException(
                    "You must specify a filter condition before executing this operation.",
                    operation="count",
                    suggestions=[
                        "Use .where() to add a filter condition",
                        "Use .all() to count all records"
                    ]
                )

            self.__resolve_key_conditions()
            self.__validate_index()

            filter_expression = None
            if self._filter_expression:
                filter_expression = transform_params_in_filter(self._filter_expression)

            if self._key_condition_expression and not self._force_scan and not self._scan_all:
                key_condition = transform_params_in_query(self._key_condition_expression)
                total = self._count_query(key_condition, filter_expression, self._index)
            else:
                total = self._count_scan(filter_expression)

            self.__reset_query_builder()
            return total
        except DynoLayerException as e:
            if self.raise_on_error:
                raise
            self._last_error = e
            self.__reset_query_builder()
            return 0

    @classmethod
    def find_or_fail(cls, key: dict, message="Record not found.", attributes: List[str] = None) -> Optional[DynoLayer]:
        cls._class_last_error = None
        try:
            instance = cls.get_item(key, attributes=attributes)
            if instance is None and cls._class_last_error is None:
                raise RecordNotFoundException(message, key=key, entity=cls.__name__)
            return instance
        except DynoLayerException as e:
            if cls.raise_on_error:
                raise
            cls._class_last_error = e
            return None

    def _load_indexes(self):
        from dynolayer.crud_mixin import CrudMixin

        cache_key = f"{self._entity}:indexes"
        if cache_key in CrudMixin._table_keys_cache:
            indexes = CrudMixin._table_keys_cache[cache_key]
        else:
            table_description = self._describe()["Table"]
            indexes = {}
            for idx in table_description.get("GlobalSecondaryIndexes", []):
                idx_schema = idx["KeySchema"]
                idx_hash = next(a["AttributeName"] for a in idx_schema if a["KeyType"] == "HASH")
                idx_range = next((a["AttributeName"] for a in idx_schema if a["KeyType"] == "RANGE"), None)
                indexes[idx["IndexName"]] = {
                    "keys": [a["AttributeName"] for a in idx_schema],
                    "hash_key": idx_hash,
                    "range_key": idx_range,
                }
            for idx in table_description.get("LocalSecondaryIndexes", []):
                idx_schema = idx["KeySchema"]
                idx_hash = next(a["AttributeName"] for a in idx_schema if a["KeyType"] == "HASH")
                idx_range = next((a["AttributeName"] for a in idx_schema if a["KeyType"] == "RANGE"), None)
                indexes[idx["IndexName"]] = {
                    "keys": [a["AttributeName"] for a in idx_schema],
                    "hash_key": idx_hash,
                    "range_key": idx_range,
                }
            CrudMixin._table_keys_cache[cache_key] = indexes

        self._indexes = indexes
        self._all_index_keys = {key for idx in indexes.values() for key in idx["keys"]}

    def __apply_auto_id(self):
        if self._auto_id is None:
            return

        pk_field = self._partition_keys[0]
        if pk_field in self._data and self._data[pk_field] is not None:
            return

        if self._auto_id in ("uuid4", "uuid1", "uuid7"):
            self._data[pk_field] = self.__generate_uuid_id()
        elif self._auto_id == "numeric":
            self._data[pk_field] = self.__generate_numeric_id()

    def __generate_uuid_id(self):
        generators = {
            "uuid4": uuid.uuid4,
            "uuid1": uuid.uuid1,
        }

        if self._auto_id == "uuid7":
            if hasattr(uuid, "uuid7"):
                generators["uuid7"] = uuid.uuid7
            else:
                warnings.warn("uuid7 requires Python 3.14+. Falling back to uuid4.", RuntimeWarning, stacklevel=4)
                generators["uuid7"] = uuid.uuid4

        generated = str(generators[self._auto_id]())

        if self._auto_id_length is not None:
            return generated.replace("-", "")[:self._auto_id_length]

        return generated

    def __generate_numeric_id(self):
        table_name = self._auto_id_table or DynoConfig.get("auto_id_table")
        try:
            response = self._get_dynamodb().Table(table_name).update_item(
                Key={"entity": self._entity},
                UpdateExpression="ADD #counter :inc",
                ExpressionAttributeNames={"#counter": "current_value"},
                ExpressionAttributeValues={":inc": 1},
                ReturnValues="UPDATED_NEW"
            )
            return int(response["Attributes"]["current_value"])
        except Exception as e:
            if "ResourceNotFoundException" in type(e).__name__ or "ResourceNotFound" in str(e):
                raise AutoIdException(
                    f"Sequences table '{table_name}' not found. "
                    f"Create it with partition key 'entity' (String).",
                    strategy="numeric",
                    entity=self._entity
                )
            raise

    def __generate_numeric_id_batch(self, count):
        table_name = self._auto_id_table or DynoConfig.get("auto_id_table")
        try:
            response = self._get_dynamodb().Table(table_name).update_item(
                Key={"entity": self._entity},
                UpdateExpression="ADD #counter :inc",
                ExpressionAttributeNames={"#counter": "current_value"},
                ExpressionAttributeValues={":inc": count},
                ReturnValues="UPDATED_NEW"
            )
            end = int(response["Attributes"]["current_value"])
            return list(range(end - count + 1, end + 1))
        except Exception as e:
            if "ResourceNotFoundException" in type(e).__name__ or "ResourceNotFound" in str(e):
                raise AutoIdException(
                    f"Sequences table '{table_name}' not found. "
                    f"Create it with partition key 'entity' (String).",
                    strategy="numeric",
                    entity=self._entity
                )
            raise

    def __resolve_key_conditions(self):
        if self._force_scan or self._scan_all:
            return

        if self._index:
            valid_keys = set(self._indexes[self._index]["keys"]) if self._index in self._indexes else set()
        else:
            valid_keys = set(self._partition_keys)

        resolved_key_conditions = []
        for cond in self._key_condition_expression:
            attr = next(iter(cond))
            if attr in valid_keys:
                resolved_key_conditions.append(cond)
            else:
                self._filter_expression.append({"AND": {attr: cond[attr]}})

        resolved_filter = []
        for filt in self._filter_expression:
            operator = next(iter(filt))
            inner = filt[operator]
            attr = next(iter(inner))
            if attr in valid_keys:
                resolved_key_conditions.append({attr: inner[attr]})
            else:
                resolved_filter.append(filt)

        self._key_condition_expression = resolved_key_conditions
        self._filter_expression = resolved_filter

    def __validate_key_dict(self, key: dict):
        missing = [k for k in self._partition_keys if k not in key]
        if missing:
            raise ValidationException(
                f"Missing primary key(s): {', '.join(missing)}.",
                required_fields=self._partition_keys
            )

    def __validate_index(self):
        if not self._index:
            return

        if self._index not in self._indexes:
            raise QueryException(
                f"Index '{self._index}' does not exist on table '{self._entity}'.",
                operation="get",
                suggestions=[f"Available indexes: {', '.join(self._indexes.keys())}"]
            )

        index_info = self._indexes[self._index]
        condition_keys = set()
        for cond in self._key_condition_expression:
            condition_keys.update(cond.keys())

        partition_key = index_info["hash_key"]
        if partition_key not in condition_keys:
            raise QueryException(
                f"Index '{self._index}' requires partition key '{partition_key}' in the query condition.",
                operation="get",
                suggestions=[f"Add .where('{partition_key}', <value>) to your query"]
            )

    def __validate_required_fields(self, custom_data: List[str] = None):
        required = self._required_fields
        if custom_data and len(custom_data) > 0:
            required = list(set(required + custom_data))

        for field in required:
            if (self._data.get(field) is None) or (hasattr(self._data.get(field), '__len__') and len(self._data.get(field)) == 0):
                raise ValidationException(
                    f"Field '{field}' is required but missing or empty.",
                    field=field,
                    required_fields=required
                )

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
        keys = set(self._partition_keys) | self._all_index_keys
        if attribute in keys:
            self._key_condition_expression.append({attribute: (condition, value)})
        else:
            self._filter_expression.append({filter_operator: {attribute: (condition, value)}})

    def __reset_query_builder(self):
        self._index = None
        self._limit = None
        self._project_expression = None
        self._key_condition_expression = list()
        self._filter_expression = list()
        self._force_scan = False
        self._offset = None
        self._scan_all = False