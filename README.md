# DynoLayer

Uma biblioteca Python para DynamoDB que traz a elegância do Eloquent ORM (Laravel) para suas aplicações serverless. Baseada no padrão Active Record, o DynoLayer oferece uma interface fluente e intuitiva para trabalhar com tabelas DynamoDB.

## Features

- **Active Record Pattern**: Defina models que representam tabelas DynamoDB
- **Fluent Query Builder**: Encadeie métodos para construir queries complexas
- **Collections**: Trabalhe com resultados usando métodos similares ao Eloquent
- **Timestamps Automáticos**: Gerenciamento opcional de `created_at` e `updated_at` (numérico ou ISO 8601)
- **Proteção de Mass Assignment**: Whitelist de campos para prevenir dados indesejados
- **Suporte a Índices**: Query usando Global e Local Secondary Indexes
- **Auto-ID**: Geração automática de IDs (UUID v4/v1/v7 ou numérico incremental) por model
- **Batch Operations**: Operações em lote para create, find e destroy
- **Escrita Condicional**: `unique=True` no create e condições no save para escrita segura
- **Transações**: Escrita e leitura transacional atômica via `transact_write`/`transact_get`
- **Configuração Centralizada**: API de configuração para credenciais AWS, timestamps e retry
- **Type Safety**: Conversão automática de tipos e resolução inteligente de key conditions

## Instalação

```bash
pip install dynolayer
```

Ou com boto3 incluído:

```bash
pip install dynolayer[full]
```

> Requer Python 3.9+

## Quick Start

### Configuração

```python
from dynolayer import DynoLayer

# Em Lambda (produção) — IAM role cuida das credenciais
DynoLayer.configure(
    timestamp_format="numeric",              # "numeric" (unix int) ou "iso" (ISO 8601)
    timestamp_timezone="America/Sao_Paulo",  # Timezone para timestamps
)

# Dev local com LocalStack
DynoLayer.configure(
    endpoint_url="http://localhost:4566",
    region="us-east-1",
)

# Dev local com AWS profile
DynoLayer.configure(profile_name="my-dev-profile")
```

### Definir um Model

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",                           # Nome da tabela DynamoDB
            required_fields=["email", "name"],        # Campos obrigatórios
            fillable=["id", "email", "name", "role"], # Campos permitidos para mass assignment
            timestamps=True,                          # Gerenciar created_at/updated_at automaticamente
            partition_key="id",                       # Partition key da tabela
        )
```

### Criar Registros

```python
# Criar usando class method
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
})

# Ou criar usando instância
user = User()
user.id = 1
user.email = "john@example.com"
user.name = "John Doe"
user.save()

# Criar em lote
users = User.batch_create([
    {"id": 1, "email": "john@example.com", "name": "John", "role": "admin"},
    {"id": 2, "email": "jane@example.com", "name": "Jane", "role": "admin"},
    {"id": 3, "email": "bob@example.com", "name": "Bob", "role": "common"},
])
```

### Consultar Registros

```python
# Buscar todos os registros
users = User.all().get()

# Buscar por chave primária
user = User.find({"id": 1})

# Buscar vários por chave primária (batch)
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

# Query com condições
admins = (
    User.where("role", "admin")
    .and_where("status", "active")
    .index("role-index")
    .get()
)

# Queries complexas
recent_admins = (
    User.where("role", "admin")
    .where_between("created_at", yesterday, today)
    .where_not("email", "contains", "test")
    .limit(100)
    .get()
)
```

### Atualizar Registros

```python
user = User.find({"id": 1})
user.name = "Jane Doe"
user.save()
```

### Deletar Registros

```python
# Deletar instância
user = User.find({"id": 1})
user.destroy()

# Ou deletar por chave
User.delete({"id": 1})

# Deletar em lote
User.batch_destroy([{"id": 1}, {"id": 2}, {"id": 3}])
```

## Configuração

O DynoLayer oferece uma API de configuração centralizada via `DynoLayer.configure()`.

### Opções disponíveis

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `region` | `AWS_REGION` ou `"sa-east-1"` | Região AWS |
| `endpoint_url` | `None` | URL customizada (LocalStack, DynamoDB Local) |
| `aws_access_key_id` | `None` | Chave de acesso AWS (usa IAM role se não definido) |
| `aws_secret_access_key` | `None` | Chave secreta AWS |
| `profile_name` | `None` | Nome do perfil AWS CLI |
| `timestamp_format` | `"numeric"` | Formato dos timestamps: `"numeric"` (unix int) ou `"iso"` (ISO 8601) |
| `timestamp_timezone` | `TIMESTAMP_TIMEZONE` ou `"America/Sao_Paulo"` | Timezone para timestamps |
| `retry_max_attempts` | `3` | Máximo de tentativas para retry |
| `retry_mode` | `"adaptive"` | Modo de retry do boto3: `"standard"` ou `"adaptive"` |
| `auto_id_table` | `"dynolayer_sequences"` | Tabela de sequências para IDs numéricos |

### Prioridade de resolução

```
parâmetro do model  →  DynoLayer.configure()  →  variáveis de ambiente  →  defaults
     (maior)                                                                (menor)
```

### Override por model

```python
class Logs(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="logs",
            fillable=["id", "message", "level"],
            timestamps=True,
            timestamp_format="iso",  # Override apenas para este model
            partition_key="id",
        )
```

## Collections

Resultados de queries são retornados como objetos `Collection`:

```python
users = User.where("role", "admin").get()

# Iterar sobre resultados
for user in users:
    print(user.name)

# Primeiro item
admin = users.first()

# Contar resultados
print(f"Encontrados {users.count()} admins")

# Extrair um atributo
emails = users.pluck("email")
# ["john@example.com", "jane@example.com", ...]

# Converter para lista de dicts
data = users.to_list()
# [{"id": 1, "name": "John", ...}, ...]
```

## Query Builder

O DynoLayer oferece uma interface fluente e encadeável para construir queries:

### Operadores de Comparação

```python
User.where("age", ">", 18).get()
User.where("status", "=", "active").get()
User.where("score", ">=", 100).get()
```

Operadores suportados: `=`, `<`, `<=`, `>`, `>=`, `<>`, `begins_with`, `contains`

### Encadeamento de Condições

```python
# Condições AND
users = (
    User.where("role", "admin")
    .and_where("status", "active")
    .and_where("age", ">=", 18)
    .get()
)

# Condições OR
users = (
    User.where("role", "admin")
    .or_where("role", "moderator")
    .get()
)

# Condições NOT
users = User.where_not("status", "banned").get()
```

### Queries de Range e Conjuntos

```python
# BETWEEN
from datetime import datetime, timedelta, timezone

yesterday = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
today = int(datetime.now(timezone.utc).timestamp())

users = User.where_between("created_at", yesterday, today).get()

# IN
users = User.where_in("status", ["active", "pending", "trial"]).get()
```

### Operações com Strings

```python
# Begins with
users = User.where("email", "begins_with", "john").get()

# Contains
users = User.where("name", "contains", "Smith").get()
```

### Usando Índices

```python
# Query usando Global Secondary Index
users = (
    User.where("role", "admin")
    .index("role-index")
    .get()
)

# Índice composto
users = (
    User.where("role", "admin")
    .and_where("email", "begins_with", "john")
    .index("role-email-index")
    .get()
)
```

### Limit e Projeção

```python
# Limitar resultados
users = User.where("role", "admin").limit(10).get()

# Selecionar atributos específicos
users = User.all().attributes_to_get(["id", "email", "name"]).get()
```

### Count

```python
# Contar registros (otimizado — não carrega dados na memória)
total = User.all().count()
admins_count = User.where("role", "admin").index("role-index").count()
```

### Query vs Scan

O DynoLayer escolhe automaticamente entre Query e Scan. Force um scan quando necessário:

```python
users = (
    User.where("age", ">", 18)
    .or_where("status", "premium")
    .force_scan()
    .get()
)
```

## Batch Operations

Operações em lote para melhor performance, especialmente em AWS Lambda:

```python
# Criar vários registros de uma vez
users = User.batch_create([
    {"id": 1, "email": "john@example.com", "name": "John", "role": "admin"},
    {"id": 2, "email": "jane@example.com", "name": "Jane", "role": "admin"},
])

# Buscar vários por chave primária
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

# Deletar vários
User.batch_destroy([{"id": 1}, {"id": 2}, {"id": 3}])
```

O chunking automático é aplicado (25 items para write/delete, 100 para get), com retry de itens não processados.

## Paginação

```python
# Paginação automática — busca todas as páginas
all_users = User.all().get(return_all=True)

# Paginação manual para APIs
limit = 50
query = User.all().limit(limit)

# Aplicar offset da página anterior
if last_evaluated_key:
    query = query.offset(last_evaluated_key)

results = query.fetch()

# Dados de paginação
next_key = User().last_evaluated_key()
count = User().get_count()
```

## API Reference

### Configuração

| Método | Descrição |
|--------|-----------|
| `DynoLayer.configure(**kwargs)` | Configurar credenciais AWS, timestamps e retry |

### Class Methods

| Método | Descrição |
|--------|-----------|
| `all()` | Iniciar query para todos os registros |
| `find(key)` | Buscar registro por chave primária |
| `find_or_fail(key, message)` | Buscar ou lançar exceção |
| `where(*args)` | Iniciar query builder |
| `create(data, unique)` | Criar e salvar registro (`unique=True` previne sobrescrita) |
| `delete(key)` | Deletar registro por chave |
| `batch_create(items)` | Criar vários registros em lote |
| `batch_find(keys)` | Buscar vários por chave primária |
| `batch_destroy(keys)` | Deletar vários registros em lote |
| `transact_write(operations)` | Escrita transacional atômica (até 25 operações) |
| `transact_get(requests)` | Leitura transacional atômica |
| `prepare_put(data)` | Preparar operação Put para transação |
| `prepare_delete(key)` | Preparar operação Delete para transação |
| `prepare_update(key, data)` | Preparar operação Update para transação |

### Métodos do Query Builder

| Método | Descrição |
|--------|-----------|
| `where(attr, operator, value)` | Adicionar condição WHERE |
| `and_where(attr, operator, value)` | Adicionar condição AND |
| `or_where(attr, operator, value)` | Adicionar condição OR |
| `where_not(attr, operator, value)` | Adicionar condição NOT |
| `where_between(attr, start, end)` | Adicionar condição BETWEEN |
| `where_in(attr, values)` | Adicionar condição IN |
| `index(name)` | Especificar índice a usar |
| `limit(count)` | Limitar resultados |
| `offset(last_evaluated_key)` | Definir ponto de início da paginação |
| `attributes_to_get(attrs)` | Selecionar atributos específicos |
| `force_scan()` | Forçar scan ao invés de query |
| `get(return_all)` | Executar e retornar Collection |
| `fetch(return_all)` | Alias para get() |
| `count()` | Contar registros (otimizado com Select=COUNT) |

### Métodos de Instância

| Método | Descrição |
|--------|-----------|
| `save(condition)` | Criar ou atualizar registro (com condição opcional) |
| `destroy()` | Deletar registro atual |
| `data()` | Obter dicionário interno de dados |
| `fillable()` | Obter lista de campos preenchíveis |
| `last_evaluated_key()` | Token de paginação da última query |
| `get_count()` | Contagem de itens retornados na última query |

### Métodos da Collection

| Método | Descrição |
|--------|-----------|
| `first()` | Primeiro item ou None |
| `count()` | Contagem de itens |
| `pluck(key)` | Extrair um atributo de todos os itens |
| `to_list()` | Converter para lista de dicionários |

## Documentação

- [Getting Started](docs/getting-started.md) - Instalação e uso básico
- [Query Builder](docs/query-builder.md) - Guia completo de queries
- [Collections](docs/collections.md) - Trabalhando com resultados
- [Advanced Features](docs/advanced.md) - Configuração, paginação, timestamps e mais

## Licença

MIT

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para enviar um Pull Request.