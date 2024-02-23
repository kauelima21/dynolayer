import boto3
import json
import uuid
import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
from decimal import Decimal


class DynoLayer:
    def __init__(
            self,
            entity: str,
            required_fields: list,
            partition_key: str = 'id',
            timestamps: bool = True
    ) -> None:
        load_dotenv()
        self._entity = entity
        self._required_fields = required_fields
        self._partition_key = partition_key
        self._timestamps = timestamps
        self._limit = 50
        self._offset = False
        self._order_by = None
        self._count = None
        self._secondary_index = None
        self._attributes_to_get = None
        self._filter_expression = None
        self._filter_params = None
        self._filter_params_name = None
        self._last_evaluated_key = None
        self._error = None
        self._is_find_by = False
        self._is_query_operation = False
        self._just_count = False
        self._region = 'sa-east-1'
        self._dynamodb = self._load_dynamo()
        self._table = self._dynamodb.Table(self._entity)
        self._data = {}

    def __setattr__(self, name, value):
        if '_data' in self.__dict__ and name not in self.__dict__:
            self._data[name] = value
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name: str):
        if '_data' in self.__dict__ and isinstance(self._data, dict):
            return self._data.get(name)
        else:
            return object.__getattribute__(self, name)

    # Chamado apenas pelas classes filhas do DynoLayer
    def _transform_into_layer(self, item: dict):
        cls = self.__class__
        new_item = cls.__new__(cls)
        new_item.__dict__ = self.__dict__.copy()
        new_item._data = {}  # limpa os antigos atributos
        for key, value in item.items():
            setattr(new_item, key, value)
        return new_item

    def _load_dynamo(self):
        endpoint_url = None
        if os.environ.get('LOCAL_ENDPOINT'):
            endpoint_url = os.environ.get('LOCAL_ENDPOINT')
        if os.environ.get('REGION'):
            self._region = os.environ.get('REGION')
        return boto3.resource(
            'dynamodb',
            region_name=self._region,
            endpoint_url=endpoint_url
        )

    """
    Args:
    key (str): The table key to filter on.
    key_value: The value to use on the filter.

    Returns:
    self: The DynoLayer.
    """

    def query_by(self, key: str, key_value, secondary_index=None):
        self._is_query_operation = True
        self._secondary_index = secondary_index
        return self.find_by(key, key_value)

    """
    Args:
    filter_expression (str): The filter expression string.
    filter_params (dict): The filter params.

    Returns:
    self: The DynoLayer.
    """

    def find(
            self,
            filter_expression: str = None,
            filter_params: dict = None,
            filter_params_name: dict = None
    ):
        self._filter_expression = filter_expression
        self._filter_params = filter_params
        self._filter_params_name = filter_params_name
        return self

    def query(
            self,
            filter_expression: str,
            filter_params: dict,
            filter_params_name: dict,
            index_or_partition_key
    ):
        self._is_query_operation = True
        self._secondary_index = index_or_partition_key
        self._filter_expression = filter_expression
        self._filter_params = filter_params
        self._filter_params_name = filter_params_name
        return self

    """
    Args:
    attribute (str): The table attribute to filter on.
    attribute_value: The value to use on the filter.

    Returns:
    self: The DynoLayer.
    """

    def find_by(self, attribute: str, attribute_value):
        self._is_find_by = True

        if isinstance(attribute_value, dict) or isinstance(attribute_value, list):
            attribute_value = json.dumps(attribute_value)

        self._filter_expression = f'#{attribute} = :{attribute}'
        self._filter_params = {
            f':{attribute}': attribute_value
        }
        self._filter_params_name = {
            f'#{attribute}': attribute
        }

        return self

    """
    Args:
    attributes (str): The specific attributes to return from table.

    Returns:
    self: The DynoLayer.
    """

    def attributes_to_get(self, attributes: str):
        str_attributes_to_get = attributes
        if self._is_find_by:
            str_attributes_to_get = ''
            for attr in attributes.split(','):
                str_attributes_to_get += f'#{attr},'
                self._filter_params_name.update({f'#{attr}': attr})

            str_attributes_to_get = str_attributes_to_get[:-1]
        self._attributes_to_get = str_attributes_to_get
        return self

    """
    Args:
    limit (int): The limit of records to return from table.

    Returns:
    self: The DynoLayer.
    """

    def limit(self, limit: int = 50):
        self._limit = limit
        return self

    """
    Returns:
    int: The count of records retrieved from the table after an operation.
    """

    @property
    def get_count(self) -> int:
        return self._count

    """
    Returns:
    int: The total count of records in the table.
    """

    def count(self):
        self._fetch(just_count=True)
        return self._count

    """
    Returns:
    bool: Indicate if the operation must paginate in a last_evaluated_key.
    """

    def offset(self, last_evaluated_key):
        self._last_evaluated_key = last_evaluated_key
        self._offset = True
        return self

    def order(self, attribute: str, is_ascending: bool = True):
        self._order_by = {'attribute': attribute, 'is_ascending': is_ascending}
        return self

    """
    Returns:
    dict: The last record's key retrieved from the table.
    """

    @property
    def last_evaluated_key(self) -> dict:
        return self._last_evaluated_key

    """
    Args:
    paginate_through_results (bool): Indicate if the result should be paginated.

    Returns:
    list: The record collection from table.
    """

    def fetch(self, paginate_through_results: bool = False, object=False):
        return self._fetch(paginate_through_results, object=object)

    def _fetch(self, paginate_through_results: bool = False, just_count=False, object=False):
        try:
            scan_params = {
                'TableName': self._entity,
                'Limit': self._limit,
            }

            if just_count:
                scan_params.update({'Select': 'COUNT'})

            if self._filter_expression:
                filter_key = 'KeyConditionExpression' if self._is_query_operation else 'FilterExpression'
                scan_params.update({filter_key: self._filter_expression})
                scan_params.update({'ExpressionAttributeValues': self._filter_params})
                scan_params.update({'ExpressionAttributeNames': self._filter_params_name})

            if self._attributes_to_get:
                scan_params.update({'ProjectionExpression': self._attributes_to_get})

            if self._secondary_index:
                scan_params.update({'IndexName': self._secondary_index})

            if self._is_query_operation:
                return self._order_response(self._fetch_query(scan_params, paginate_through_results), object=object)

            return self._order_response(self._fetch_scan(scan_params, paginate_through_results), object=object)
        except Exception as e:
            self._error = str(e)
            return None

    """
    Args:
    partition_key (str): The table's partition Key.

    Returns:
    self: The founded record as DynoLayer.
    """

    def find_by_id(self, partition_key: str):
        try:
            response = self._table.get_item(
                TableName=self._entity,
                Key={
                    self._partition_key: partition_key
                }
            )
            for key, value in response['Item'].items():
                if isinstance(value, Decimal):
                    value = int(value)
                setattr(self, key, value)
            return self
        except Exception as e:
            self._error = str(e)
            return None

    """
    Returns:
    bool: True for successful put/update item. False if something went wrong.
    """

    def save(self) -> bool:
        if not self._required():
            self._error = 'All required fields must be setted'
            return False
        # update
        if self._data.get(self._partition_key):
            partition_key = self._data.get(self._partition_key)
            try:
                update_expression = 'SET'
                expression_values = {}
                expression_names = {}

                for key, value in self._safe():
                    update_expression += f' #{key} = :{key},'
                    if isinstance(value, dict) or isinstance(value, list):
                        value = json.dumps(value)
                    expression_values[f':{key}'] = value
                    expression_names[f'#{key}'] = key

                update_expression = update_expression[:-1]

                self._table.update_item(
                    Key={
                        self._partition_key: partition_key
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values,
                    ExpressionAttributeNames=expression_names,
                    ReturnValues='ALL_NEW'
                )
                return True
            except Exception as e:
                self._error = str(e)
                return False

        # create
        try:
            data = {self._partition_key: str(uuid.uuid4())}

            for key, value in self._safe():
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                data[key] = value

            self._table.put_item(
                Item=data
            )
            self.id = data[self._partition_key]
            return True
        except Exception as e:
            self._error = str(e)
            return False

    """
    Returns:
    bool: True for successful delete item. False if the record does not exist.
    """

    def destroy(self) -> bool:
        partition_key = self._data.get(self._partition_key, None)

        if not partition_key:
            return False

        try:
            self._table.delete_item(
                TableName=self._entity,
                Key={
                    self._partition_key: partition_key
                }
            )
            return True
        except Exception as e:
            self._error = str(e)
            return False

    """
    Returns:
    str: Return the error occurred during an operation.
    """

    @property
    def error(self) -> str:
        return self._error

    """
    Returns:
    dict_items: The _data items without the partition key.
    """

    def _safe(self):
        if self._timestamps:
            zone = os.environ.get('TIMESTAMP_TIMEZONE') if os.environ.get('TIMESTAMP_TIMEZONE',
                                                                          None) else 'America/Sao_Paulo'
            timezone = pytz.timezone(zone)
            current_date = datetime.now(timezone)
            if not self._data.get(self._partition_key):
                self._data['created_at'] = int(current_date.timestamp())
            self._data['updated_at'] = int(current_date.timestamp())

        safe = list(self._data.items())
        for item in safe:
            if self._partition_key in item:
                safe.remove(item)
                break
        return dict(safe).items()

    """
    Returns:
    bool: True if the required fields are satisfied.
    """

    def _required(self):
        required = True
        if len(self._required_fields) == 0:
            return required
        for key, value in self._data.items():
            if key not in self._required_fields:
                required = False
            else:
                required = True
                break
        return required

    def _fetch_scan(self, scan_params: dict, paginate_through_results: bool):
        response = None
        data = []

        if self._offset:
            scan_params.update({'ExclusiveStartKey': self._last_evaluated_key})
            response = self._table.scan(**scan_params)
            data = response.get('Items', None)
            self._count = response['Count']
        else:
            response = self._table.scan(**scan_params)
            data = response.get('Items', None)
            self._count = response['Count']

        if response.get('LastEvaluatedKey', None):
            self._last_evaluated_key = response['LastEvaluatedKey']

        if paginate_through_results:
            while 'LastEvaluatedKey' in response:
                scan_params.update({'ExclusiveStartKey': response['LastEvaluatedKey']})
                response = self._table.scan(**scan_params)
                data.extend(response.get('Items', None))
                self._count += response['Count']
                self._last_evaluated_key = response['LastEvaluatedKey']

        return data

    def _fetch_query(self, scan_params: dict, paginate_through_results: bool):
        response = None
        data = []

        if self._offset:
            scan_params.update({'ExclusiveStartKey': self._last_evaluated_key})
            response = self._table.query(**scan_params)
            data = response.get('Items', None)
            self._count = response['Count']
        else:
            response = self._table.query(**scan_params)
            data = response.get('Items', None)
            self._count = response['Count']

        if response.get('LastEvaluatedKey', None):
            self._last_evaluated_key = response['LastEvaluatedKey']

        if paginate_through_results:
            while 'LastEvaluatedKey' in response:
                scan_params.update({'ExclusiveStartKey': response['LastEvaluatedKey']})
                response = self._table.query(**scan_params)
                data.extend(response.get('Items', None))
                self._count += response['Count']
                self._last_evaluated_key = response['LastEvaluatedKey']

        return data

    def data(self):
        return self._data

    """
    Args:
    response (list): The response to order.

    Returns:
    list: The ordered filtered or not.
    """

    def _order_response(self, response, object=False):
        if len(response) == 0:
            return response

        if self._order_by:
            response = sorted(
                response,
                key=lambda d: d[self._order_by.get('attribute')],
                reverse=not self._order_by.get('is_ascending')
            )

        for item in response:
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = int(value)

        transformed_response = []
        if object:
            for item in response:
                transformed_response.append(self._transform_into_layer(item))
            return transformed_response

        return response
