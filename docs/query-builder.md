# Query Builder

DynoLayer provides a fluent, chainable query builder similar to Laravel's Eloquent. Build complex queries with an intuitive API.

## Expression Queries (find)

O método `find()` oferece uma API expressiva para construir queries e scans com expression strings:

### Sintaxe básica

```python
# Scan geral (todos os registros)
users = User().find().fetch(True)

# Query por partition key
users = User().find("role = :r", r="admin").index("role-index").fetch(True)

# Múltiplas condições
users = User().find(
    "role = :r AND status = :s",
    r="admin", s="active"
).index("role-index").fetch(True)
```

### Operadores suportados

| Operador | Sintaxe | Exemplo |
|----------|---------|---------|
| Igual | `attr = :val` | `"user_id = :uid"` |
| Diferente | `attr <> :val` | `"status <> :s"` |
| Menor que | `attr < :val` | `"age < :max"` |
| Menor ou igual | `attr <= :val` | `"age <= :max"` |
| Maior que | `attr > :val` | `"age > :min"` |
| Maior ou igual | `attr >= :val` | `"age >= :min"` |
| Começa com | `attr begins_with :val` | `"name begins_with :prefix"` |
| Contém | `attr contains :val` | `"tags contains :tag"` |
| Está em | `attr in :val` | `"status in :list"` (valor deve ser lista) |
| Entre | `attr between :start and :end` | `"age between :min and :max"` |
| Existe | `attr exists` | `"email exists"` (sem placeholder) |
| Não existe | `attr not_exists` | `"phone not_exists"` (sem placeholder) |
| Tipo do atributo | `attr attribute_type :val` | `"data attribute_type :t"` |

### Conectores lógicos

| Conector | Exemplo |
|----------|---------|
| `AND` | `"user_id = :uid AND status = :s"` |
| `OR` | `"city = :c1 OR city = :c2"` |
| `AND NOT` | `"user_id = :uid AND NOT status = :s"` |
| `OR NOT` | `"user_id = :uid OR NOT archived = :a"` |

### Exemplos completos

```python
# Between
orders = Order().find(
    "created_at between :start and :end",
    start="2024-01-01", end="2024-12-31"
).fetch(True)

# Exists / Not exists (sem placeholder)
users = User().find("email exists").fetch(True)
users = User().find("phone not_exists").fetch(True)

# Combinação complexa
addresses = Address().find(
    "user_id = :uid AND email exists AND NOT status = :s",
    uid="123", s="deleted"
).index("user-index").limit(50).fetch(True)

# Com paginação
page1 = User().find("role = :r", r="admin").index("role-index").limit(10).fetch()
last_key = User().last_evaluated_key

page2 = User().find("role = :r", r="admin").index("role-index").limit(10).offset(last_key).fetch()
```

## Where Query Builder

O query builder com `where()` continua disponível para quem prefere a API encadeada:

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

By default, DynamoDB returns up to 1MB of data. Use `paginate=True` to automatically fetch all pages. Combine with `all=True` to get the full `Collection`:

```python
# Get all results across all pages
all_users = User.where("role", "admin").get(all=True, paginate=True)
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
            timestamps=True,
            partition_key="id",
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
| `find(expression, **values)` | Unified query/scan with expression string |
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
| `get(all=False, paginate=False)` | Execute query (single model by default; `all=True` → Collection; `paginate=True` → follow all pages) |
| `fetch(all=False, paginate=False)` | Alias for `get()` |