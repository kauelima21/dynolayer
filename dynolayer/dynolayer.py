import boto3
import json
import uuid
import pytz
from datetime import datetime


class DynoLayer:
    def __init__(
            self,
            entity: str,
            required_fields: list,
            partition_key: str = 'id',
            timestamps: bool = True,
            region='sa-east-1'
        ) -> None:
        self._entity = entity
        self._required_fields = required_fields
        self._partition_key = partition_key
        self._timestamps = timestamps
        self._region = region
        self._limit = 50
        self._count = None
        self._attributes_to_get = None
        self._filter_expression = None
        self._filter_params = None
        self._filter_params_name = None
        self._error = None
        self._dynamodb = boto3.resource('dynamodb', region_name=self._region)
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

    """
    Returns:
    bool: True for successful put/update item. False if something went wrong.
    """
    def save(self) -> bool:
        if (not self._required()):
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
            data = {}
            data[self._partition_key] = str(uuid.uuid4())

            for key, value in self._safe():
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                data[key] = value

            self._table.put_item(
                Item=data
            )
            return True
        except:
            self._error = str(e)
            return False

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
        if filter_expression:
            self._filter_expression = filter_expression
            self._filter_params = filter_params
            self._filter_params_name = filter_params_name
        return self

    """
    Args:
    attribute (str): The table attribute to filter on.
    attributes_to_get (str): Attributes to get from table. If it's empty, will bring all attributes.

    Returns:
    self: The DynoLayer.
    """
    def find_by(self, attribute: str, attribute_value, attributes_to_get: str = None):
        if isinstance(attribute_value, dict) or isinstance(attribute_value, list):
            attribute_value = json.dumps(attribute_value)

        self._filter_expression = f'#{attribute} = :{attribute}'
        self._filter_params = {
            f':{attribute}': attribute_value
        }
        self._filter_params_name = {
            f'#{attribute}': attribute
        }

        if attributes_to_get:
            str_attributes_to_get = ''
            for attr in attributes_to_get.split(','):
                str_attributes_to_get += f'#{attr},'
                self._filter_params_name.update({f'#{attr}': attr})

            self._attributes_to_get = str_attributes_to_get[:-1]

        return self

    """
    Args:
    attributes (str): The specific attributes to return from table.

    Returns:
    self: The DynoLayer.
    """
    def attributes_to_get(self, attributes: str):
        self._attributes_to_get = attributes
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
    int: The count of records retrived from the table.
    """
    @property
    def count(self) -> int:
        return self._count

    """
    Returns:
    str: Return the error occurred during an operation.
    """
    @property
    def error(self) -> str:
        return self._error

    """
    Args:
    paginate_through_results (bool): Indicate if the result should be paginated.

    Returns:
    list: The record collection from table.
    """
    def fetch(self, paginate_through_results: bool = False):
        try:
            scan_params = {
                'TableName': self._entity,
                'Limit': self._limit
            }

            if self._filter_expression:
                scan_params.update({'FilterExpression': self._filter_expression})
                scan_params.update({'ExpressionAttributeValues': self._filter_params})
                scan_params.update({'ExpressionAttributeNames': self._filter_params_name})

            if self._attributes_to_get:
                scan_params.update({'ProjectionExpression': self._attributes_to_get})

            response = self._table.scan(**scan_params)
            data = response['Items']
            self._count = response['Count']
            if paginate_through_results:
                while 'LastEvaluatedKey' in response:
                    scan_params.update({'ExclusiveStartKey': response['LastEvaluatedKey']})
                    response = self._table.scan(**scan_params)
                    data.extend(response['Items'])
                    self._count += response['Count']

            return data
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
                setattr(self, key, value)
            return self
        except Exception as e:
            self._error = str(e)
            return None

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
    dict_items: The _data items without the partition key.
    """
    def _safe(self):
        if self._timestamps:
            timezone = pytz.timezone('America/Sao_Paulo')
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
