# Advanced Features

## Configuração

O DynoLayer oferece uma API de configuração centralizada via `DynoLayer.configure()`. Chame uma vez no início da aplicação (handler da Lambda, bootstrap, etc).

### AWS Lambda (produção)

Na Lambda, as credenciais vêm automaticamente do IAM Role:

```python
from dynolayer import DynoLayer

DynoLayer.configure(
    timestamp_format="iso",
    timestamp_timezone="America/Sao_Paulo",
)
```

### Desenvolvimento local

Com LocalStack ou DynamoDB Local:

```python
DynoLayer.configure(
    endpoint_url="http://localhost:4566",
    region="us-east-1",
)
```

Com AWS CLI profile:

```python
DynoLayer.configure(profile_name="my-dev-profile")
```

Com credenciais explícitas:

```python
DynoLayer.configure(
    aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region="us-east-1",
)
```

### Retry automático

O DynoLayer configura retry automático com backoff para erros do DynamoDB (throttling, etc):

```python
DynoLayer.configure(
    retry_max_attempts=5,       # Padrão: 3
    retry_mode="adaptive",      # "standard" ou "adaptive" (padrão)
)
```

O modo `adaptive` ajusta automaticamente a taxa de requests baseado nos erros de throttling.

### Prioridade de resolução

```
parâmetro do model  →  DynoLayer.configure()  →  variáveis de ambiente  →  defaults
     (maior)                                                                (menor)
```

### Referência de opções

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `region` | `AWS_REGION` ou `"sa-east-1"` | Região AWS |
| `endpoint_url` | `None` | URL customizada (LocalStack, DynamoDB Local) |
| `aws_access_key_id` | `None` | Chave de acesso AWS |
| `aws_secret_access_key` | `None` | Chave secreta AWS |
| `profile_name` | `None` | Nome do perfil AWS CLI |
| `timestamp_format` | `"numeric"` | `"numeric"` (unix int) ou `"iso"` (ISO 8601) |
| `timestamp_timezone` | `TIMESTAMP_TIMEZONE` ou `"America/Sao_Paulo"` | Timezone para timestamps |
| `retry_max_attempts` | `3` | Máximo de tentativas |
| `retry_mode` | `"adaptive"` | Modo de retry do boto3 |

## Timestamps

O DynoLayer gerencia automaticamente os campos `created_at` e `updated_at`.

### Habilitando timestamps

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"],
            timestamps=True
        )
```

### Como funciona

Quando `timestamps=True`:

- **created_at**: Definido automaticamente ao criar um novo registro
- **updated_at**: Definido automaticamente ao criar ou atualizar um registro

### Formatos de timestamp

O DynoLayer suporta dois formatos de timestamp:

| Formato | Tipo | Exemplo |
|---------|------|---------|
| `numeric` | `int` | `1735132800` (Unix timestamp) |
| `iso` | `str` | `"2026-04-05T14:30:00-03:00"` (ISO 8601 com timezone) |

#### Configuração global

```python
DynoLayer.configure(timestamp_format="iso")
```

#### Override por model

```python
class Logs(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="logs",
            fillable=["id", "message", "level"],
            timestamps=True,
            timestamp_format="iso",  # Apenas este model usa ISO
        )

class Metrics(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="metrics",
            fillable=["id", "value", "metric_name"],
            timestamps=True,
            # Usa o formato da configuração global (padrão: "numeric")
        )
```

### Exemplos

```python
# Com timestamp_format="numeric" (padrão)
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe"
})
print(user.created_at)  # 1735132800
print(user.updated_at)  # 1735132800

# Com timestamp_format="iso"
log = Logs.create({
    "id": 1,
    "message": "User logged in",
    "level": "info"
})
print(log.created_at)  # "2026-04-05T14:30:00-03:00"
print(log.updated_at)  # "2026-04-05T14:30:00-03:00"
```

### Timezone

O timezone padrão é `America/Sao_Paulo`. Para alterar:

```python
# Via configuração
DynoLayer.configure(timestamp_timezone="UTC")

# Ou via variável de ambiente
# export TIMESTAMP_TIMEZONE=UTC
```

## Batch Operations

Operações em lote para melhor performance, especialmente em AWS Lambda onde o tempo de execução é custo.

### batch_create

Cria vários registros de uma vez. Valida `required_fields` e `fillable` para cada item:

```python
users = User.batch_create([
    {"id": 1, "email": "john@example.com", "name": "John", "role": "admin"},
    {"id": 2, "email": "jane@example.com", "name": "Jane", "role": "admin"},
    {"id": 3, "email": "bob@example.com", "name": "Bob", "role": "common"},
])

# Retorna lista de instâncias do model
for user in users:
    print(f"{user.name} criado com sucesso")
```

### batch_find

Busca vários registros por chave primária:

```python
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

# Retorna Collection
for user in users:
    print(user.name)

emails = users.pluck("email")
```

### batch_destroy

Deleta vários registros por chave primária:

```python
User.batch_destroy([{"id": 1}, {"id": 2}, {"id": 3}])
```

### Chunking automático

O DynoLayer aplica chunking automático respeitando os limites do DynamoDB:

- **Write/Delete**: 25 itens por batch (via `batch_writer`)
- **Get**: 100 itens por batch (via `batch_get_item`)

Itens não processados são automaticamente reenviados.

## Paginação

O DynamoDB retorna resultados em páginas (até 1MB por página). O DynoLayer oferece suporte a paginação automática e manual.

### Paginação automática

Use `return_all=True` para buscar todas as páginas automaticamente:

```python
# Buscar todos os registros de todas as páginas
all_users = User.all().get(return_all=True)
```

### Paginação manual

Para controle fino da paginação (útil para APIs):

```python
limit = 50
user = User()

# Contar total (otimizado — não carrega dados na memória)
total_count = user.all().count()

# Construir query
query = user.all().limit(limit)

# Aplicar offset se fornecido pelo cliente
last_evaluated_key = request.get('last_evaluated_key')
if last_evaluated_key:
    query = query.offset(last_evaluated_key)

# Executar query
results = query.fetch()

# Dados de paginação
results_count = user.get_count()
next_key = user.last_evaluated_key()

# Construir resposta da API
response = {
    'total_count': total_count,
    'results': results.to_list(),
    'results_count': results_count,
    'last_evaluated_key': next_key  # Passar ao cliente para a próxima página
}
```

### Propriedades de paginação

Após executar uma query, acesse os dados de paginação:

- `user.last_evaluated_key()`: Token de paginação do DynamoDB (chaves do último item)
- `user.get_count()`: Número de itens retornados nesta página

### Count otimizado

O método `count()` usa `Select='COUNT'` do DynamoDB, retornando apenas a contagem sem transferir dados:

```python
# Contar todos os registros
total = User.all().count()

# Contar com filtro
admins = User.where("role", "admin").index("role-index").count()
```

## Method Overriding (Polimorfismo)

Sobrescreva métodos do DynoLayer para personalizar o comportamento dos seus models.

### Validação customizada

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
        # Validação customizada antes de salvar
        if not self._is_valid_email(self.email):
            return False

        # Chamar o save do pai
        return super().save()

    def _is_valid_email(self, email):
        return "@" in email and "." in email
```

Uso:

```python
user = User()
user.id = 1
user.email = "invalid.com"
print(user.save())  # False

user.email = "valid@example.com"
print(user.save())  # True
```

### Lógica de negócio customizada

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
        # Auto-calcular total
        if hasattr(self, 'items') and self.items:
            self.total = sum(item['price'] * item['quantity'] for item in self.items)

        # Status padrão
        if not hasattr(self, 'status'):
            self.status = "pending"

        return super().save()

    def mark_as_paid(self):
        self.status = "paid"
        return self.save()
```

Uso:

```python
order = Order()
order.id = 1
order.user_id = 100
order.items = [
    {"product": "Widget", "price": 10.0, "quantity": 2},
    {"product": "Gadget", "price": 25.0, "quantity": 1},
]
order.save()

print(order.total)   # 45.0 (auto-calculado)
print(order.status)  # "pending" (auto-definido)

order.mark_as_paid()
print(order.status)  # "paid"
```

## Validação de Campos

### Campos obrigatórios

Campos definidos em `required_fields` devem estar presentes ao criar registros:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email", "name"],
            fillable=["id", "email", "name", "role"]
        )


# Isso falha — campos obrigatórios ausentes
user = User.create({"id": 1})  # Erro: email e name são obrigatórios

# Isso funciona
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe"
})
```

### Proteção de mass assignment

Apenas campos em `fillable` podem ser atribuídos:

```python
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email"],
            fillable=["id", "email", "name"]  # Apenas estes podem ser atribuídos
        )


user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "is_admin": True  # IGNORADO (não está em fillable)
})

print(hasattr(user, 'is_admin'))  # False
```

## Tipos de Dados Complexos

O DynoLayer suporta os tipos complexos do DynamoDB:

### Objetos aninhados

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

print(user.profile)
# {"age": 30, "city": "São Paulo", "preferences": {...}}
```

### Listas

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

### Precisão numérica

O DynamoDB requer `Decimal` para números. O DynoLayer converte floats automaticamente:

```python
product = Product.create({
    "id": 1,
    "name": "Widget",
    "price": 29.99  # Convertido automaticamente para Decimal
})
```

## Boas Práticas

### Use índices nas suas queries

Sempre use índices para queries eficientes:

```python
# Bom — usa índice
users = (
    User.where("role", "admin")
    .index("role-index")
    .get()
)

# Ruim — força scan custoso
users = User.where("role", "admin").force_scan().get()
```

### Limite os resultados

Sempre limite os resultados ao que você precisa:

```python
# Bom — busca apenas o necessário
users = User.where("role", "admin").limit(100).get()

# Ruim — pode retornar milhões de registros
users = User.where("role", "admin").get(return_all=True)
```

### Use projeção

Busque apenas os atributos que você precisa:

```python
# Bom — busca apenas campos necessários
users = (
    User.all()
    .attributes_to_get(["id", "email"])
    .get()
)

# Ruim — busca todos os atributos
users = User.all().get()
```

### Use batch operations

Para operações com múltiplos registros, prefira métodos batch:

```python
# Bom — uma chamada batch
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])

# Ruim — três chamadas individuais
user1 = User.find({"id": 1})
user2 = User.find({"id": 2})
user3 = User.find({"id": 3})
```

### Valide seus dados

Sempre valide dados nos seus models:

```python
class User(DynoLayer):
    def save(self):
        if not self._validate():
            raise ValueError("Dados do usuário inválidos")
        return super().save()

    def _validate(self):
        if not hasattr(self, 'email') or '@' not in self.email:
            return False
        if hasattr(self, 'age') and self.age < 0:
            return False
        return True
```