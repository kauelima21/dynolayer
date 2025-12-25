# Getting Started

## Installation

Install DynoLayer using pip:

```bash
pip install dynolayer
```

Or with boto3 included:

```bash
pip install dynolayer[aws]
```

## Configuration

DynoLayer uses boto3 to connect to DynamoDB. Set your AWS region via environment variable:

```bash
export AWS_REGION=sa-east-1
```

Make sure your AWS credentials are configured (via environment variables, AWS credentials file, or IAM roles).

## Your First Model

DynoLayer follows the Active Record pattern, similar to Laravel's Eloquent. Each model class represents a DynamoDB table.

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",                           # Table name
            required_fields=["email", "name"],        # Required fields
            fillable=["id", "email", "name", "role"], # Mass-assignable fields
            timestamps=True                           # Auto-manage created_at/updated_at
        )
```

### Model Configuration

- **entity**: DynamoDB table name
- **required_fields**: Fields that must be present when creating records
- **fillable**: Whitelist of fields that can be mass-assigned (protection against unwanted data)
- **timestamps**: When `True`, automatically adds `created_at` and `updated_at` fields

## Basic Usage

### Create a record

```python
# Using the create method
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
})

# Using save method
user = User()
user.id = 1
user.email = "john@example.com"
user.name = "John Doe"
user.role = "admin"
user.save()
```

### Retrieve records

```python
# Get all users
users = User.all()

# Find by primary key
user = User.find({"id": 1})

# Find or raise exception
user = User.find_or_fail({"id": 1}, "User not found")
```

### Update a record

```python
user = User.find({"id": 1})
user.name = "Jane Doe"
user.save()
```

### Delete a record

```python
# Delete instance
user = User.find({"id": 1})
user.delete()

# Or use destroy method
User.destroy({"id": 1})
```

## Next Steps

- Learn about the [Query Builder](query-builder.md) for advanced filtering
- Explore [Collections](collections.md) for working with result sets
- Check [Advanced Features](advanced.md) for pagination, polymorphism, and more