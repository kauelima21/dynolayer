import os

import boto3


class CrudMixin:
    _dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "sa-east-1"))
    _client = boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "sa-east-1"))

    def __init__(self, entity: str):
        self._entity = entity
        self._partition_keys, self._indexes = self._get_index_keys()

    @property
    def _table(self):
        return self._dynamodb.Table(self._entity)

    def _describe(self):
        return self._client.describe_table(TableName=self._entity)

    @staticmethod
    def _get_current_timestamp():
        import pytz

        from datetime import datetime

        timezone = pytz.timezone(os.environ.get("TIMESTAMP_TIMEZONE", "America/Sao_Paulo"))
        current_time = datetime.now(timezone)

        return int(current_time.timestamp())

    def _get_index_keys(self):
        table_description = self._describe()["Table"]

        indexes = list()
        primary_keys = [attr["AttributeName"] for attr in table_description["KeySchema"]]
        for index in table_description.get("GlobalSecondaryIndexes", []):
            indexes.extend([attr["AttributeName"] for attr in index["KeySchema"]])

        for index in table_description.get("LocalSecondaryIndexes", []):
            indexes.extend([attr["AttributeName"] for attr in index["KeySchema"]])

        return primary_keys, indexes

    def _put(self, data: dict):
        self._table.put_item(Item=data)

        return True

    def _delete(self, key: dict):
        self._table.delete_item(Key=key)

        return True

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
               limit=None, return_all=False, pe=None):
        query_attributes = {"KeyConditionExpression": key_condition}

        if filter_expression:
            query_attributes["FilterExpression"] = filter_expression

        if limit:
            query_attributes["Limit"] = limit

        if index:
            query_attributes["IndexName"] = index

        if pe:
            query_attributes["ProjectionExpression"] = pe

        response = self._table.query(**query_attributes)
        data = response["Items"]
        if return_all:
            while "LastEvaluatedKey" in response:
                query_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.query(**query_attributes)
                data.extend(response["Items"])

        return data

    def _scan(self, filter_expression: str, limit=None, return_all=False, pe=None):
        scan_attributes = {"FilterExpression": filter_expression}

        if limit:
            scan_attributes["Limit"] = limit

        if pe:
            scan_attributes["ProjectionExpression"] = pe

        response = self._table.scan(**scan_attributes)
        data = response["Items"]
        if return_all:
            while "LastEvaluatedKey" in response:
                scan_attributes["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.scan(**scan_attributes)
                data.extend(response["Items"])

        return data
