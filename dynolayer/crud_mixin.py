import boto3
from botocore.config import Config

from dynolayer.config import DynoConfig


class CrudMixin:
    _dynamodb = None
    _client = None
    _table_keys_cache = {}

    @classmethod
    def _get_session(cls):
        profile_name = DynoConfig.get("profile_name")
        if profile_name:
            return boto3.Session(profile_name=profile_name)
        return boto3.Session()

    @classmethod
    def _get_dynamodb(cls):
        if cls._dynamodb is None:
            cls._dynamodb = cls._get_session().resource(
                "dynamodb",
                **cls._build_boto_kwargs(),
            )
        return cls._dynamodb

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = cls._get_session().client(
                "dynamodb",
                **cls._build_boto_kwargs(),
            )
        return cls._client

    @classmethod
    def _build_boto_kwargs(cls):
        kwargs = {
            "region_name": DynoConfig.get("region"),
            "config": Config(
                retries={
                    "max_attempts": DynoConfig.get("retry_max_attempts"),
                    "mode": DynoConfig.get("retry_mode"),
                }
            ),
        }

        endpoint_url = DynoConfig.get("endpoint_url")
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        aws_access_key_id = DynoConfig.get("aws_access_key_id")
        aws_secret_access_key = DynoConfig.get("aws_secret_access_key")
        if aws_access_key_id and aws_secret_access_key:
            kwargs["aws_access_key_id"] = aws_access_key_id
            kwargs["aws_secret_access_key"] = aws_secret_access_key

        return kwargs

    @classmethod
    def _reset_boto_clients(cls):
        CrudMixin._dynamodb = None
        CrudMixin._client = None
        CrudMixin._table_keys_cache.clear()

    def __init__(self, entity: str):
        self._entity = entity
        self._partition_keys, self._indexes = self._get_index_keys()

    @property
    def _table(self):
        return self._get_dynamodb().Table(self._entity)

    def _describe(self):
        return self._get_client().describe_table(TableName=self._entity)

    def _get_current_timestamp(self, timestamp_format=None):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        fmt = timestamp_format or DynoConfig.get("timestamp_format")
        tz_name = DynoConfig.get("timestamp_timezone")
        timezone = ZoneInfo(tz_name)
        current_time = datetime.now(timezone)

        if fmt == "iso":
            return current_time.isoformat()

        return int(current_time.timestamp())

    def _get_index_keys(self):
        if self._entity in CrudMixin._table_keys_cache:
            return CrudMixin._table_keys_cache[self._entity]

        table_description = self._describe()["Table"]

        indexes = list()
        primary_keys = [attr["AttributeName"] for attr in table_description["KeySchema"]]
        for index in table_description.get("GlobalSecondaryIndexes", []):
            indexes.extend([attr["AttributeName"] for attr in index["KeySchema"]])

        for index in table_description.get("LocalSecondaryIndexes", []):
            indexes.extend([attr["AttributeName"] for attr in index["KeySchema"]])

        CrudMixin._table_keys_cache[self._entity] = (primary_keys, indexes)
        return primary_keys, indexes

    def _put(self, data: dict):
        self._table.put_item(Item=data)

        return True

    def _delete(self, key: dict):
        self._table.delete_item(Key=key)

        return True

    def _batch_put(self, items: list):
        with self._table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)

        return True

    def _batch_delete(self, keys: list):
        with self._table.batch_writer() as batch:
            for key in keys:
                batch.delete_item(Key=key)

        return True

    def _batch_get(self, keys: list):
        all_items = []

        for i in range(0, len(keys), 100):
            chunk = keys[i:i + 100]
            response = self._get_dynamodb().batch_get_item(
                RequestItems={
                    self._entity: {"Keys": chunk}
                }
            )
            all_items.extend(response.get("Responses", {}).get(self._entity, []))

            unprocessed = response.get("UnprocessedKeys", {})
            while unprocessed.get(self._entity):
                response = self._get_dynamodb().batch_get_item(RequestItems=unprocessed)
                all_items.extend(response.get("Responses", {}).get(self._entity, []))
                unprocessed = response.get("UnprocessedKeys", {})

        return all_items

    def _update(self, data: dict, index_key: dict):
        expression_values = dict()
        expression_names = dict()
        update_expression = list()

        for key, value in data.items():
            expression_values[f":{key}"] = value
            expression_names[f"#{key}"] = key
            update_expression.append(f"#{key} = :{key}")

        update_expression = "SET " + ", ".join(update_expression)

        self._table.update_item(
            Key=index_key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues="UPDATED_NEW",
        )

        return True

    def _query(self, key_condition: str, filter_expression=None, index=None,
               limit=None, return_all=False, pe=None, offset=None):
        query_attributes = {"KeyConditionExpression": key_condition}

        if filter_expression:
            query_attributes["FilterExpression"] = filter_expression

        if limit:
            query_attributes["Limit"] = limit

        if index:
            query_attributes["IndexName"] = index

        if pe:
            query_attributes["ProjectionExpression"] = pe

        if offset:
            query_attributes["ExclusiveStartKey"] = offset

        response = self._table.query(**query_attributes)
        data = response["Items"]
        if return_all:
            while "LastEvaluatedKey" in response:
                query_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.query(**query_attributes)
                data.extend(response["Items"])

        return {
            "Items": data,
            "Count": response.get("Count", len(data)),
            "LastEvaluatedKey": response.get("LastEvaluatedKey")
        }

    def _count_query(self, key_condition, filter_expression=None, index=None):
        query_attributes = {
            "KeyConditionExpression": key_condition,
            "Select": "COUNT",
        }

        if filter_expression:
            query_attributes["FilterExpression"] = filter_expression

        if index:
            query_attributes["IndexName"] = index

        total = 0
        response = self._table.query(**query_attributes)
        total += response.get("Count", 0)

        while "LastEvaluatedKey" in response:
            query_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self._table.query(**query_attributes)
            total += response.get("Count", 0)

        return total

    def _count_scan(self, filter_expression=None):
        scan_attributes = {"Select": "COUNT"}

        if filter_expression:
            scan_attributes["FilterExpression"] = filter_expression

        total = 0
        response = self._table.scan(**scan_attributes)
        total += response.get("Count", 0)

        while "LastEvaluatedKey" in response:
            scan_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self._table.scan(**scan_attributes)
            total += response.get("Count", 0)

        return total

    def _scan(self, filter_expression: str, limit=None, return_all=False, pe=None, offset=None):
        scan_attributes = {}

        if filter_expression:
            scan_attributes["FilterExpression"] = filter_expression

        if limit:
            scan_attributes["Limit"] = limit

        if pe:
            scan_attributes["ProjectionExpression"] = pe

        if offset:
            scan_attributes["ExclusiveStartKey"] = offset

        response = self._table.scan(**scan_attributes)
        data = response["Items"]
        if return_all:
            while "LastEvaluatedKey" in response:
                scan_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.scan(**scan_attributes)
                data.extend(response["Items"])

        return {
            "Items": data,
            "Count": response.get("Count", len(data)),
            "LastEvaluatedKey": response.get("LastEvaluatedKey")
        }