# DynoLayer

A Python library for DynamoDB that brings the elegance of Laravel's Eloquent ORM to your serverless applications. Built on the Active Record pattern, DynoLayer provides an intuitive, fluent interface for working with DynamoDB tables.

## Features

- **Active Record Pattern**: Define models that represent DynamoDB tables
- **Fluent Query Builder**: Chain methods to build complex queries
- **Eloquent-like Collections**: Work with result sets using familiar methods
- **Automatic Timestamps**: Optional `created_at` and `updated_at` management
- **Mass Assignment Protection**: Whitelist fields to prevent unwanted data
- **Index Support**: Query using Global and Local Secondary Indexes
- **Type Safety**: Automatic type conversion for DynamoDB compatibility

## Installation

```bash
pip install dynolayer
```

Or with boto3 included:

```bash
pip install dynolayer[aws]
```

## Quick Start

### Define a Model

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",                           # DynamoDB table name
            required_fields=["email", "name"],        # Required fields
            fillable=["id", "email", "name", "role"], # Mass-assignable fields
            timestamps=True                           # Auto-manage created_at/updated_at
        )
```

### Create Records

```python
# Create using class method
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
})

# Or create using instance
user = User()
user.id = 1
user.email = "john@example.com"
user.name = "John Doe"
user.save()
```

### Query Records

```python
# Get all records
users = User.all()

# Find by primary key
user = User.find({"id": 1})

# Query with conditions
admins = (
    User.where("role", "admin")
    .and_where("status", "active")
    .index("role-index")
    .get()
)

# Complex queries
recent_admins = (
    User.where("role", "admin")
    .where_between("created_at", yesterday, today)
    .where_not("email", "contains", "test")
    .limit(100)
    .get()
)
```

### Update Records

```python
user = User.find({"id": 1})
user.name = "Jane Doe"
user.save()
```

### Delete Records

```python
# Delete instance
user = User.find({"id": 1})
user.delete()

# Or delete by key
User.destroy({"id": 1})
```

## Working with Collections

Query results are returned as `Collection` objects with helpful methods:

```python
users = User.where("role", "admin").get()

# Iterate over results
for user in users:
    print(user.name)

# Get first item
admin = users.first()

# Count results
print(f"Found {users.count()} admins")

# Extract single attribute
emails = users.pluck("email")
# ["john@example.com", "jane@example.com", ...]

# Convert to list of dicts
data = users.to_list()
# [{"id": 1, "name": "John", ...}, ...]
```

## Query Builder

DynoLayer provides a fluent, chainable interface for building queries:

### Comparison Operators

```python
User.where("age", ">", 18).get()
User.where("status", "=", "active").get()
User.where("score", ">=", 100).get()
```

Supported operators: `=`, `<`, `<=`, `>`, `>=`, `<>`, `begins_with`, `contains`

### Chaining Conditions

```python
# AND conditions
users = (
    User.where("role", "admin")
    .and_where("status", "active")
    .and_where("age", ">=", 18)
    .get()
)

# OR conditions
users = (
    User.where("role", "admin")
    .or_where("role", "moderator")
    .get()
)

# NOT conditions
users = User.where_not("status", "banned").get()
```

### Range and Set Queries

```python
# BETWEEN
from datetime import datetime, timedelta, timezone

yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
today = int(datetime.now(timezone.utc).timestamp())

users = User.where_between("created_at", yesterday, today).get()

# IN
users = User.where_in("status", ["active", "pending", "trial"]).get()
```

### String Operations

```python
# Begins with
users = User.where("email", "begins_with", "john").get()

# Contains
users = User.where("name", "contains", "Smith").get()
```

### Using Indexes

```python
# Query using Global Secondary Index
users = (
    User.where("role", "admin")
    .index("role-index")
    .get()
)

# Composite index
users = (
    User.where("role", "admin")
    .and_where("email", "begins_with", "john")
    .index("role-email-index")
    .get()
)
```

### Limiting and Projection

```python
# Limit results
users = User.where("role", "admin").limit(10).get()

# Select specific attributes
users = User.all().attributes_to_get(["id", "email", "name"]).get()
```

### Query vs Scan

DynoLayer automatically chooses between Query and Scan. Force a scan when needed:

```python
users = (
    User.where("age", ">", 18)
    .or_where("status", "premium")
    .force_scan()
    .get()
)
```

## Advanced Features

### Timestamps

Enable automatic timestamp management:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            fillable=["id", "email", "name"],
            timestamps=True  # Adds created_at and updated_at
        )
```

Timestamps are stored as Unix timestamps in UTC.

### Pagination

```python
# Automatic pagination - fetches all pages
all_users = User.all().get(return_all=True)

# Manual pagination for APIs
limit = 50
query = User.all().limit(limit)

# Apply offset from previous page
if last_evaluated_key:
    query = query.offset(last_evaluated_key)

results = query.fetch()

# Get pagination data
next_key = User().last_evaluated_key
count = User().get_count
```

### Method Overriding

Customize model behavior by overriding methods:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"]
        )

    def save(self):
        # Custom validation
        if not self._is_valid_email(self.email):
            return False

        # Call parent save
        return super().save()

    def _is_valid_email(self, email):
        return "@" in email and "." in email
```

### Field Validation

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email", "name"],  # Required on create
            fillable=["id", "email", "name"],   # Only these can be assigned
        )
```

Required fields must be present when creating records. Non-fillable fields are automatically filtered out.

### Complex Data Types

DynoLayer supports nested objects and lists:

```python
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "profile": {
        "age": 30,
        "preferences": {
            "theme": "dark"
        }
    },
    "phones": ["+1234567890", "+0987654321"]
})
```

## Configuration

### AWS Region

```bash
export AWS_REGION=sa-east-1
```

Default region is `sa-east-1` if not specified.

### AWS Credentials

DynoLayer uses boto3 for AWS authentication. Credentials can be provided via:

- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS credentials file (`~/.aws/credentials`)
- IAM roles (for EC2, Lambda, etc.)

## API Reference

### Class Methods

| Method | Description |
|--------|-------------|
| `all()` | Retrieve all records as Collection |
| `find(key)` | Find record by primary key |
| `find_or_fail(key, message)` | Find or raise exception |
| `where(*args)` | Start query builder |
| `create(data)` | Create and save record |
| `destroy(key)` | Delete record by key |

### Query Builder Methods

| Method | Description |
|--------|-------------|
| `where(attr, operator, value)` | Add WHERE condition |
| `and_where(attr, operator, value)` | Add AND condition |
| `or_where(attr, operator, value)` | Add OR condition |
| `where_not(attr, operator, value)` | Add NOT condition |
| `where_between(attr, start, end)` | Add BETWEEN condition |
| `where_in(attr, values)` | Add IN condition |
| `index(name)` | Specify index to use |
| `limit(count)` | Limit results |
| `attributes_to_get(attrs)` | Select specific attributes |
| `force_scan()` | Force scan instead of query |
| `get(return_all)` | Execute and return Collection |
| `fetch(return_all)` | Alias for get() |

### Instance Methods

| Method | Description |
|--------|-------------|
| `save()` | Create or update record |
| `delete()` | Delete current record |
| `data()` | Get internal data dictionary |
| `fillable()` | Get fillable fields list |

### Collection Methods

| Method | Description |
|--------|-------------|
| `first()` | Get first item or None |
| `count()` | Count of items |
| `pluck(key)` | Extract single attribute from all items |
| `to_list()` | Convert to list of dictionaries |

## Documentation

- [Getting Started](docs/getting-started.md) - Installation and basic usage
- [Query Builder](docs/query-builder.md) - Comprehensive query guide
- [Collections](docs/collections.md) - Working with result sets
- [Advanced Features](docs/advanced.md) - Pagination, polymorphism, timestamps, and more

## Examples

### Complete CRUD Example

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email", "name"],
            fillable=["id", "email", "name", "role", "status"],
            timestamps=True
        )


# Create
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
})

# Read
user = User.find({"id": 1})
all_users = User.all()

# Update
user.name = "Jane Doe"
user.save()

# Delete
user.delete()
```

### Query Example

```python
from datetime import datetime, timedelta, timezone

# Complex query with multiple conditions
yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
today = int(datetime.now(timezone.utc).timestamp())

active_admins = (
    User.where("role", "admin")
    .and_where("status", "active")
    .where_between("created_at", yesterday, today)
    .where_not("email", "contains", "test")
    .index("role-index")
    .limit(100)
    .attributes_to_get(["id", "email", "name"])
    .get()
)

# Process results
for admin in active_admins:
    print(f"{admin.name} - {admin.email}")

print(f"Found {active_admins.count()} admins")
```

### Custom Validation Example

```python
class Order(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="orders",
            required_fields=["user_id", "total"],
            fillable=["id", "user_id", "items", "total", "status"],
            timestamps=True
        )

    def save(self):
        # Auto-calculate total from items
        if hasattr(self, 'items') and self.items:
            self.total = sum(item['price'] * item['quantity'] for item in self.items)

        # Set default status
        if not hasattr(self, 'status'):
            self.status = "pending"

        return super().save()

    def mark_as_paid(self):
        self.status = "paid"
        return self.save()


# Usage
order = Order()
order.id = 1
order.user_id = 100
order.items = [
    {"product": "Widget", "price": 10.0, "quantity": 2},
    {"product": "Gadget", "price": 25.0, "quantity": 1},
]
order.save()

print(order.total)   # 45.0 (auto-calculated)
print(order.status)  # "pending"

order.mark_as_paid()
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.