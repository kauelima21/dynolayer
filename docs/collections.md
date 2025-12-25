# Collections

DynoLayer returns query results as `Collection` objects, similar to Laravel's Eloquent Collections. This provides a convenient, fluent interface for working with result sets.

## What is a Collection?

A Collection is an iterable wrapper around query results that provides helpful methods for data manipulation.

```python
users = User.where("role", "admin").get()
# users is a Collection instance
```

## Iterating Over Collections

Collections are iterable, so you can use them in loops:

```python
users = User.all()

for user in users:
    print(f"{user.name} - {user.email}")
```

## Collection Methods

### first()

Get the first item in the collection, or `None` if empty:

```python
users = User.where("role", "admin").get()
admin = users.first()

if admin:
    print(admin.name)
```

### count()

Get the number of items in the collection:

```python
users = User.where("role", "admin").get()
print(f"Found {users.count()} admins")
```

### len()

Collections support Python's built-in `len()` function:

```python
users = User.all()
print(f"Total users: {len(users)}")
```

### pluck()

Extract a single attribute from all items:

```python
users = User.all()

# Get all emails as a list
emails = users.pluck("email")
# ["john@example.com", "jane@example.com", ...]

# Get all IDs
ids = users.pluck("id")
# [1, 2, 3, ...]
```

If an item doesn't have the requested attribute, `None` is returned for that item:

```python
users = User.all()
roles = users.pluck("role")
# ["admin", None, "moderator", ...]
```

### to_list()

Convert the collection to a list of dictionaries:

```python
users = User.where("role", "admin").get()
data = users.to_list()

# [
#     {"id": 1, "name": "John", "email": "john@example.com", "role": "admin"},
#     {"id": 2, "name": "Jane", "email": "jane@example.com", "role": "admin"},
#     ...
# ]
```

This is useful for JSON serialization or passing data to templates:

```python
import json

users = User.all()
json_data = json.dumps(users.to_list())
```

## Working with Individual Items

Each item in a collection is a model instance with attribute access:

```python
users = User.where("role", "admin").get()

for user in users:
    # Access attributes directly
    print(user.id)
    print(user.name)
    print(user.email)

    # Get raw data as dict
    user_data = user.data()

    # Modify and save
    user.status = "verified"
    user.save()
```

## Practical Examples

### Check if results exist

```python
users = User.where("email", "contains", "@example.com").get()

if users.count() > 0:
    print(f"Found {users.count()} users with @example.com emails")
else:
    print("No users found")
```

### Get first or default

```python
admin = User.where("role", "admin").get().first()

if admin is None:
    print("No admin found")
else:
    print(f"Admin: {admin.name}")
```

### Extract specific data

```python
# Get all admin emails
admins = User.where("role", "admin").get()
admin_emails = admins.pluck("email")

# Send notification to all admins
for email in admin_emails:
    send_notification(email)
```

### Process and transform

```python
users = User.where("status", "active").get()

# Build a lookup dictionary
user_lookup = {user.id: user.name for user in users}

# Or create a summary
summary = [
    {"id": user.id, "email": user.email}
    for user in users
]
```

### Combine with other operations

```python
# Get recent users and convert to list for JSON response
from datetime import datetime, timedelta, timezone

yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
today = int(datetime.now(timezone.utc).timestamp())

recent_users = (
    User.where_between("created_at", yesterday, today)
    .limit(10)
    .get()
)

response = {
    "count": recent_users.count(),
    "users": recent_users.to_list()
}
```

## Method Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `first()` | Model or None | Get first item or None |
| `count()` | int | Count of items |
| `len()` | int | Python len() support |
| `pluck(key)` | list | Extract single attribute from all items |
| `to_list()` | list[dict] | Convert to list of dictionaries |
| `__iter__()` | iterator | Make collection iterable |

## Empty Collections

All methods safely handle empty collections:

```python
users = User.where("role", "nonexistent").get()

users.first()      # None
users.count()      # 0
len(users)         # 0
users.pluck("id")  # []
users.to_list()    # []

for user in users: # Loop doesn't execute
    print(user)
```