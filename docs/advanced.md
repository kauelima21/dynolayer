# Advanced Features

## Timestamps

DynoLayer can automatically manage `created_at` and `updated_at` timestamps for your records.

### Enabling timestamps

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"],
            timestamps=True  # Enable automatic timestamps
        )
```

### How it works

When `timestamps=True`:

- **created_at**: Set automatically when creating a new record
- **updated_at**: Set automatically when creating or updating a record

Both timestamps are stored as Unix timestamps (integers) in UTC.

```python
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe"
})

print(user.created_at)  # 1735132800 (Unix timestamp)
print(user.updated_at)  # 1735132800

# Update the user
user.name = "Jane Doe"
user.save()

print(user.updated_at)  # 1735136400 (new timestamp)
```

### Timezone configuration

Default timezone is `America/Sao_Paulo`. This is currently hardcoded in the library.

## Pagination

DynamoDB returns results in pages (up to 1MB per page). DynoLayer provides built-in pagination support.

### Automatic pagination

Use `return_all=True` to automatically fetch all pages:

```python
# Get all users across all pages
all_users = User.all().get(return_all=True)
```

### Manual pagination

For better control over pagination (useful for APIs):

```python
limit = 50
user = User()

# Get total count
total_count = user.all().count()

# Build query
query = user.all().limit(limit)

# Apply offset if provided by client
last_evaluated_key = request.get('last_evaluated_key')
if last_evaluated_key:
    query = query.offset(last_evaluated_key)

# Execute query
results = query.fetch()

# Get result count and next page token
results_count = user.get_count
next_key = user.last_evaluated_key

# Build API response
response = {
    'total_count': total_count,
    'results': results.to_list(),
    'results_count': results_count,
    'last_evaluated_key': next_key  # Pass to client for next page
}
```

### Pagination properties

After executing a query, access pagination data:

- `user.last_evaluated_key`: DynamoDB's pagination token (keys of last item)
- `user.get_count`: Number of items returned in this page

## Method Overriding (Polymorphism)

Override DynoLayer methods to customize behavior for your models.

### Custom validation

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"]
        )

    def save(self):
        # Custom validation before saving
        if not self._is_valid_email(self.email):
            return False

        # Call parent save method
        return super().save()

    def _is_valid_email(self, email):
        # Simple email validation
        return "@" in email and "." in email
```

Usage:

```python
user = User()
user.id = 1
user.email = "invalid.com"
print(user.save())  # False

user.email = "valid@example.com"
print(user.save())  # True
```

### Custom business logic

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
        # Auto-calculate total
        if hasattr(self, 'items') and self.items:
            self.total = sum(item['price'] * item['quantity'] for item in self.items)

        # Set default status
        if not hasattr(self, 'status'):
            self.status = "pending"

        return super().save()

    def mark_as_paid(self):
        self.status = "paid"
        return self.save()
```

Usage:

```python
order = Order()
order.id = 1
order.user_id = 100
order.items = [
    {"product": "Widget", "price": 10.0, "quantity": 2},
    {"product": "Gadget", "price": 25.0, "quantity": 1},
]
order.save()

print(order.total)   # 45.0 (auto-calculated)
print(order.status)  # "pending" (auto-set)

order.mark_as_paid()
print(order.status)  # "paid"
```

## Field Validation

### Required fields

Fields specified in `required_fields` must be present when creating records:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email", "name"],  # Required
            fillable=["id", "email", "name", "role"]
        )


# This will fail - missing required fields
user = User.create({"id": 1})  # Error: email and name are required

# This works
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe"
})
```

### Mass assignment protection

Only fields in `fillable` can be assigned:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"]  # Only these can be assigned
        )


user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "is_admin": True  # This will be IGNORED (not in fillable)
})

print(hasattr(user, 'is_admin'))  # False
```

This protects against unwanted data being inserted into your database.

## Complex Data Types

DynoLayer supports DynamoDB's complex types:

### Nested objects

```python
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "profile": {
        "age": 30,
        "city": "São Paulo",
        "preferences": {
            "theme": "dark",
            "language": "pt-BR"
        }
    }
})

# Access nested data
print(user.profile)
# {"age": 30, "city": "São Paulo", "preferences": {...}}
```

### Lists

```python
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "phones": [
        "11 91234-5678",
        "11 95678-1234"
    ],
    "tags": ["premium", "verified"]
})

print(user.phones)  # ["11 91234-5678", "11 95678-1234"]
```

### Numeric precision

DynamoDB requires `Decimal` for numbers. DynoLayer automatically converts floats:

```python
product = Product.create({
    "id": 1,
    "name": "Widget",
    "price": 29.99  # Automatically converted to Decimal
})
```

## Environment Configuration

### AWS Region

Set the AWS region via environment variable:

```bash
export AWS_REGION=us-east-1
```

Default region is `sa-east-1` if not specified.

### AWS Credentials

DynoLayer uses boto3, which supports multiple credential sources:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM roles (for EC2, Lambda, etc.)

See [boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) for details.

## Best Practices

### Index your queries

Always use indexes for efficient queries:

```python
# Good - uses index
users = (
    User.where("role", "admin")
    .index("role-index")
    .get()
)

# Bad - forces expensive scan
users = User.where("role", "admin").force_scan().get()
```

### Limit results

Always limit results to what you need:

```python
# Good - only get what you need
users = User.where("role", "admin").limit(100).get()

# Bad - might return millions of records
users = User.where("role", "admin").get(return_all=True)
```

### Use projection

Only fetch the attributes you need:

```python
# Good - only fetch needed fields
users = (
    User.all()
    .attributes_to_get(["id", "email"])
    .get()
)

# Bad - fetches all attributes
users = User.all().get()
```

### Validate data

Always validate data in your models:

```python
class User(DynoLayer):
    def save(self):
        if not self._validate():
            raise ValueError("Invalid user data")
        return super().save()

    def _validate(self):
        if not hasattr(self, 'email') or '@' not in self.email:
            return False
        if hasattr(self, 'age') and self.age < 0:
            return False
        return True
```