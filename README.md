# DynoLayer

[![PyPI](https://img.shields.io/pypi/v/dynolayer.svg?style=flat-square)](https://pypi.org/project/dynolayer/)
[![Python](https://img.shields.io/pypi/pyversions/dynolayer.svg?style=flat-square)](https://pypi.org/project/dynolayer/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square)](LICENSE.txt)
[![Downloads](https://img.shields.io/pypi/dm/dynolayer.svg?style=flat-square)](https://pypi.org/project/dynolayer/)

###### DynoLayer is a persistence abstraction component for Amazon DynamoDB that uses boto3 under the Active Record pattern to perform common routines such as creating, reading, updating and deleting items — with a fluent query builder, typed models and first-class support for indexes, batch and transactional operations.

O DynoLayer é um componente de abstração de persistência para o Amazon DynamoDB que usa boto3 sob o padrão Active
Record para executar rotinas comuns como criar, ler, atualizar e remover itens — com query builder fluente, models
tipados e suporte de primeira classe a índices, operações em lote e transacionais.

## Sobre

###### DynoLayer was built to bring the elegance of Active Record ORMs (Eloquent, ActiveRecord) to serverless Python applications running on AWS Lambda, API Gateway and EventBridge — writing less boto3 boilerplate and doing much more.

O DynoLayer foi construído para trazer a elegância dos ORMs Active Record (Eloquent, ActiveRecord) para aplicações
Python serverless rodando em AWS Lambda, API Gateway e EventBridge — escrevendo menos boto3 boilerplate e fazendo
muito mais.

### Highlights

- Fluent query builder (Query builder fluente)
- Expression-based `find()` for query and scan (API expressiva `find()` unificando query e scan)
- Auto timestamps, numeric or ISO 8601 (Timestamps automáticos, numéricos ou ISO 8601)
- Auto ID with UUID v4/v1/v7 or numeric sequence (Auto ID com UUID v4/v1/v7 ou sequência numérica)
- Mass assignment protection via `fillable` (Proteção de mass assignment via `fillable`)
- Global and Local Secondary Indexes (Índices globais e locais)
- Batch and transactional operations (Operações em lote e transacionais)
- Centralized configuration and silent error mode (Configuração centralizada e modo silencioso de erros)

## Instalação

DynoLayer está disponível no PyPI:

```bash
pip install dynolayer
```

Ou com `boto3` incluído como dependência opcional:

```bash
pip install "dynolayer[full]"
```

> Requer Python 3.9+

## Documentação

###### For details on how to use DynoLayer, see the examples below. Each section covers a single method of the library.

Para detalhes sobre como usar o DynoLayer, veja os exemplos abaixo. Cada seção cobre um único método da biblioteca.

#### configuration

###### To start using DynoLayer, configure your AWS credentials and defaults once at application boot. When running on AWS Lambda, the IAM role already provides credentials.

Para começar a usar o DynoLayer, configure suas credenciais AWS e defaults uma vez no boot da aplicação. Em AWS
Lambda, a IAM role já provê as credenciais.

```python
from dynolayer import DynoLayer

# Produção (Lambda) — IAM role cuida das credenciais
DynoLayer.configure(
    region="sa-east-1",
    timestamp_format="numeric",              # "numeric" (unix int) ou "iso" (ISO 8601)
    timestamp_timezone="America/Sao_Paulo",
)

# Dev local com LocalStack
DynoLayer.configure(
    endpoint_url="http://localhost:4566",
    region="us-east-1",
)

# Dev local com perfil AWS
DynoLayer.configure(profile_name="my-dev-profile")
```

Opções disponíveis: `region`, `endpoint_url`, `aws_access_key_id`, `aws_secret_access_key`, `profile_name`,
`timestamp_format`, `timestamp_timezone`, `retry_max_attempts`, `retry_mode`, `auto_id_table`.

#### your model

###### DynoLayer follows the Layer Super Type and Active Record patterns. To consume it you create a model that represents your DynamoDB table and inherits from DynoLayer.

O DynoLayer segue os padrões Layer Super Type e Active Record. Para consumi-lo, crie um model que representa sua
tabela DynamoDB e herde de `DynoLayer`.

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",                             # Nome da tabela
            required_fields=["email", "name"],          # Campos obrigatórios
            fillable=["id", "email", "name", "role"],   # Mass assignment whitelist
            timestamps=True,                            # created_at/updated_at automáticos
            partition_key="id",                         # Default: "id"
            # sort_key="created_at",                    # Opcional
        )
```

#### create

```python
# Criar usando classmethod
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin",
})

# Criar com condição de unicidade (falha se PK existir)
user = User.create({"id": 1, "email": "jack@mail.com", "name": "Jack"}, unique=True)
```

#### save

###### `save()` works both for inserts (new instance) and updates (instance already loaded from the table). Conditions can be passed to guard concurrent writes.

`save()` funciona tanto para inserts (instância nova) quanto para updates (instância carregada da tabela).
Condições podem ser passadas para proteger escritas concorrentes.

```python
# Insert
user = User()
user.id = 1
user.email = "john@example.com"
user.name = "John Doe"
user.save()

# Update
user = User.get_item({"id": 1})
user.name = "John Doe"
user.save()

# Save com condição
from boto3.dynamodb.conditions import Attr
user.save(condition=Attr("role").eq("admin"))
```

#### find

###### `find()` is the expression-based query builder. It parses SQL-like strings with placeholders bound to keyword arguments — returning the model to chain `fetch()` or `get()`.

`find()` é o query builder baseado em expression strings. Ele parseia strings tipo SQL com placeholders vinculados
a kwargs — retornando o model para encadear `fetch()` ou `get()`.

```python
from datetime import datetime, timedelta, timezone

# Todos os admins
users = User().find("role = :r", r="admin").index("role-index").fetch(all=True)

# Múltiplas condições
users = (
    User().find("role = :r AND stars >= :s", r="admin", s=4)
    .index("role-index")
    .fetch(all=True)
)

# Operadores: =, <>, <, <=, >, >=, begins_with, contains, in, between
users = (
    User().find(
        "role = :r AND created_at between :start and :end AND NOT email contains :e",
        r="admin",
        start=int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp()),
        end=int(datetime.now(timezone.utc).timestamp()),
        e="test",
    )
    .index("role-index")
    .limit(100)
    .fetch(all=True)
)

# Sem argumentos: scan em toda a tabela
all_users = User().find().fetch(all=True)
```

#### get_item

###### `get_item()` fetches a single record by primary key. It accepts partition key only or composite (partition + sort).

`get_item()` busca um único registro pela chave primária. Aceita apenas partition key ou composite (partition +
sort).

```python
user = User.get_item({"id": 1})
print(user.name)

# Com projeção (atributos específicos)
user = User.get_item({"id": 1}, attributes=["id", "email"])

# Chave composta
event = Event.get_item({"user_id": "u1", "timestamp": 1700000000})
```

#### find_or_fail

###### Same as `get_item()`, but raises `RecordNotFoundException` if no record is found — even with `raise_on_error = False`.

Igual a `get_item()`, mas lança `RecordNotFoundException` se o registro não for encontrado — mesmo com
`raise_on_error = False`.

```python
user = User.find_or_fail({"id": 1})
```

#### where

###### Fluent query builder with chainable methods. Supports comparison operators, ranges, sets and string operations.

Query builder fluente encadeável. Suporta operadores de comparação, ranges, conjuntos e operações com strings.

```python
# Operadores de comparação: =, <>, <, <=, >, >=
admins = User.where("role", "admin").get(all=True)
adults = User.where("age", ">=", 18).get(all=True)

# Encadeamento AND
active_admins = (
    User.where("role", "admin")
    .and_where("status", "active")
    .get(all=True)
)

# Encadeamento OR
staff = (
    User.where("role", "admin")
    .or_where("role", "moderator")
    .get(all=True)
)

# NOT
non_banned = User.where_not("status", "banned").get(all=True)

# BETWEEN
recent = User.where_between("created_at", yesterday, today).get(all=True)

# IN
triaged = User.where_in("status", ["active", "pending", "trial"]).get(all=True)

# begins_with / contains
johns = User.where("email", "begins_with", "john").get(all=True)
smiths = User.where("name", "contains", "Smith").get(all=True)
```

#### index

###### Specify a Global or Local Secondary Index for the query. DynoLayer resolves key conditions against the index schema automatically.

Especifique um índice global ou local para a query. O DynoLayer resolve as key conditions contra o schema do
índice automaticamente.

```python
users = (
    User.where("role", "admin")
    .and_where("email", "begins_with", "j")
    .index("role-email-index")
    .get(all=True)
)
```

#### get / fetch

###### In v2.0, `get()` (and its alias `fetch()`) returns a single model by default. Pass `all=True` to get a `Collection`. Use `paginate=True` to automatically follow `LastEvaluatedKey` through every page.

Na v2.0, `get()` (e o alias `fetch()`) retorna um único model por padrão. Passe `all=True` para obter uma
`Collection`. Use `paginate=True` para seguir automaticamente o `LastEvaluatedKey` em todas as páginas.

```python
# Default: um model (ou None)
user = User.where("id", 1).get()

# Collection (página única — até 1MB do DynamoDB)
users = User.where("role", "admin").index("role-index").get(all=True)

# Collection atravessando todas as páginas
all_users = User().all().get(all=True, paginate=True)

# Paginação manual via offset + last_evaluated_key
query = User.all().limit(50)
page = query.get(all=True)
next_key = query.last_evaluated_key()

if next_key:
    next_page = User.all().limit(50).offset(next_key).get(all=True)
```

Itere sobre a Collection ou extraia dados:

```python
users = User.where("role", "admin").get(all=True)

for user in users:
    print(user.name)

admin = users.first()
total = users.count()
emails = users.pluck("email")
rows = users.to_list()
```

#### count

###### `count()` uses DynamoDB's `Select=COUNT`, so it does not transfer records over the wire.

`count()` usa `Select=COUNT` do DynamoDB, portanto não transfere os registros pela rede.

```python
total = User.all().count()
admin_count = User.where("role", "admin").index("role-index").count()
```

#### batch operations

###### Batch methods chunk requests automatically (25 items per write/delete, 100 per get) and retry unprocessed items.

Os métodos de batch fazem chunking automático (25 itens por write/delete, 100 por get) e reprocessam itens não
processados.

```python
# Criar em lote
users = User.batch_create([
    {"id": 1, "email": "a@mail.com", "name": "A"},
    {"id": 2, "email": "b@mail.com", "name": "B"},
])

# Buscar em lote
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

# Deletar em lote
User.batch_destroy([{"id": 1}, {"id": 2}])
```

#### transactions

###### Atomic multi-item writes (up to 25 operations) and reads via `transact_write` / `transact_get`.

Escritas e leituras atômicas multi-item (até 25 operações) via `transact_write` / `transact_get`.

```python
# Escrita transacional
User.transact_write([
    User.prepare_put({"id": 1, "email": "a@mail.com", "name": "A"}),
    User.prepare_update({"id": 2}, {"role": "admin"}),
    User.prepare_delete({"id": 3}),
])

# Leitura transacional
results = User.transact_get([
    {"key": {"id": 1}},
    {"key": {"id": 2}},
])
```

#### destroy

```python
# Deletar instância
user = User.get_item({"id": 1})
user.destroy()

# Deletar por chave (classmethod)
User.delete({"id": 1})
```

#### fail

###### By default (v2.0), `raise_on_error = False` — exceptions are captured and exposed via `fail()`. Subclass with `raise_on_error = True` to re-enable exceptions.

Por padrão (v2.0), `raise_on_error = False` — exceções são capturadas e expostas via `fail()`. Defina
`raise_on_error = True` na subclasse para reativar as exceções.

```python
class User(DynoLayer):
    raise_on_error = True   # opt-in estrito
    ...


# Modo silencioso (default)
user = User.create({"id": 1})  # faltando campos obrigatórios
if user is None:
    err = User.fail()           # DynoLayerException ou subclasse
    print(err)

# Em instância
user = User()
if not user.save():
    print(user.fail())
```

#### auto_id

###### Auto-generate primary keys using UUID (v4/v1/v7) or a numeric sequence persisted on a helper table.

Gere chaves primárias automaticamente usando UUID (v4/v1/v7) ou uma sequência numérica persistida em uma tabela
auxiliar.

```python
class Product(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="products",
            required_fields=["name"],
            fillable=["id", "name", "price"],
            auto_id="uuid4",           # uuid4, uuid1, uuid7 ou numeric
            # auto_id_length=22,       # trunca UUID (entre 16 e 32)
            # auto_id_table="seq",     # tabela de sequências (para auto_id="numeric")
        )


product = Product.create({"name": "Widget"})
print(product.id)  # e.g. "f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

#### timestamps

###### Automatic `created_at` and `updated_at` — numeric (Unix int) or ISO 8601 string.

`created_at` e `updated_at` automáticos — numérico (Unix int) ou string ISO 8601.

```python
# ISO 8601 (default v2.0)
class User(DynoLayer):
    def __init__(self):
        super().__init__(entity="users", fillable=["id", "email"], timestamps=True)


# Numérico por model
class LogEntry(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="logs",
            fillable=["id", "message"],
            timestamps=True,
            timestamp_format="numeric",
        )


# Numérico global
DynoLayer.configure(timestamp_format="numeric")
```

## Contribuindo

Pull requests são bem-vindos. Para mudanças relevantes, abra uma issue primeiro para discutir a proposta.

1. Faça fork do repositório
2. Crie uma branch (`git checkout -b feat/minha-feature`)
3. Rode os testes (`pytest`)
4. Abra o PR

## Suporte

###### Security: If you discover any security issue, please email the maintainer directly instead of opening a public issue.

Se você descobrir qualquer problema de segurança, envie um e-mail direto ao mantenedor em vez de abrir uma issue
pública.

## Créditos

- [Kauê Leal de Lima](https://github.com/kauelima21) (Autor)
- [Todos os contribuidores](https://github.com/kauelima21/dynolayer/contributors)

## Licença

The MIT License (MIT). Veja [LICENSE.txt](LICENSE.txt) para detalhes.
