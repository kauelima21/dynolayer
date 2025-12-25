# Query Builder

DynoLayer provides a fluent, chainable query builder similar to Laravel's Eloquent. Build complex queries with an intuitive API.

## Basic Queries

### Simple where clause

```python
# Single condition
users = User.where("role", "admin").get()

# With comparison operators
users = User.where("age", ">", 18).get()
```

### Supported operators

- `=` - Equals (default if no operator specified)
- `<` - Less than
- `<=` - Less than or equal
- `>` - Greater than
- `>=` - Greater than or equal
- `<>` - Not equal
- `begins_with` - String starts with
- `contains` - String contains

## Chaining Conditions

### AND conditions

```python
users = (
    User.where("role", "admin")
    .and_where("status", "active")
    .and_where("age", ">=", 18)
    .get()
)
```

### OR conditions

```python
users = (
    User.where("role", "admin")
    .or_where("role", "moderator")
    .get()
)
```

### NOT conditions

```python
# Exclude specific values
users = User.where_not("status", "banned").get()

# Combine with OR
users = (
    User.where("role", "admin")
    .or_where_not("status", "pending")
    .get()
)
```

## Advanced Filters

### Range queries (BETWEEN)

```python
from datetime import datetime, timedelta, timezone

yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
today = int(datetime.now(timezone.utc).timestamp())

users = (
    User.where("role", "admin")
    .where_between("created_at", yesterday, today)
    .get()
)
```

### IN operator

```python
users = (
    User.where("role", "admin")
    .where_in("status", ["active", "pending", "trial"])
    .get()
)
```

### String operations

```python
# Begins with
users = (
    User.where("role", "admin")
    .and_where("email", "begins_with", "john")
    .get()
)

# Contains
users = User.where("name", "contains", "Smith").get()
```

## Using Indexes

DynamoDB requires indexes for efficient queries. Use the `index()` method to specify which index to use.

```python
# Query using a Global Secondary Index
users = (
    User.where("role", "admin")
    .index("role-index")
    .get()
)

# Composite index (GSI with partition and sort key)
users = (
    User.where("role", "admin")
    .and_where("email", "begins_with", "john")
    .index("role-email-index")
    .get()
)
```

## Limiting Results

```python
# Get only 10 records
users = User.where("role", "admin").limit(10).get()

# Combine with other conditions
users = (
    User.where("status", "active")
    .and_where("role", "admin")
    .limit(50)
    .get()
)
```

## Selecting Specific Attributes

Use `attributes_to_get()` for projection (similar to SQL SELECT):

```python
# Single attribute
emails = User.all().attributes_to_get("email").get()

# Multiple attributes
users = User.all().attributes_to_get(["id", "email", "name"]).get()
```

## Query vs Scan

DynamoDB has two ways to retrieve data:

- **Query**: Fast, uses indexes, requires key conditions
- **Scan**: Slow, reads entire table, use for filters without keys

DynoLayer automatically chooses the best method based on your query. To force a scan:

```python
# Force scan (useful for OR conditions or non-indexed filters)
users = (
    User.where("age", ">", 18)
    .or_where("status", "premium")
    .force_scan()
    .get()
)
```

## Retrieving Results

### get() vs fetch()

Both methods are identical - `fetch()` is an alias for `get()`:

```python
users = User.where("role", "admin").get()
# Same as
users = User.where("role", "admin").fetch()
```

### Pagination

By default, DynamoDB returns up to 1MB of data. Use `return_all=True` to automatically fetch all pages:

```python
# Get all results across all pages
all_users = User.where("role", "admin").get(return_all=True)
```

See [Advanced Features](advanced.md#pagination) for manual pagination control.

## Complete Example

```python
from datetime import datetime, timedelta, timezone


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name", "role", "status", "created_at"],
            timestamps=True
        )


# Complex query
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

print(f"Found {active_admins.count()} active admins")
```

## Method Reference

| Method | Description |
|--------|-------------|
| `where(attr, operator, value)` | Add WHERE condition |
| `and_where(attr, operator, value)` | Add AND condition |
| `or_where(attr, operator, value)` | Add OR condition |
| `where_not(attr, operator, value)` | Add NOT condition |
| `or_where_not(attr, operator, value)` | Add OR NOT condition |
| `where_between(attr, start, end)` | Add BETWEEN condition |
| `where_in(attr, values)` | Add IN condition |
| `index(name)` | Specify index to use |
| `limit(count)` | Limit results |
| `attributes_to_get(attrs)` | Select specific attributes |
| `force_scan()` | Force scan instead of query |
| `get(return_all=False)` | Execute and return Collection |
| `fetch(return_all=False)` | Alias for get() |