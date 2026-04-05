# Getting Started

## Instalação

Instale o DynoLayer via pip:

```bash
pip install dynolayer
```

Ou com boto3 incluído:

```bash
pip install dynolayer[full]
```

> Requer Python 3.9+

## Configuração

### Configuração rápida

O DynoLayer oferece uma API de configuração centralizada. Chame `configure()` uma vez no início da aplicação:

```python
from dynolayer import DynoLayer

DynoLayer.configure(
    region="sa-east-1",
    timestamp_format="numeric",
    timestamp_timezone="America/Sao_Paulo",
)
```

### Em AWS Lambda (produção)

Na Lambda, as credenciais vêm automaticamente do IAM Role. Basta configurar o que precisar:

```python
DynoLayer.configure(timestamp_format="iso")
```

### Em desenvolvimento local

Com LocalStack:

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

### Prioridade de resolução

As configurações seguem esta prioridade (da maior para a menor):

```
parâmetro do model  →  DynoLayer.configure()  →  variáveis de ambiente  →  defaults
```

Por exemplo, se `AWS_REGION` está definida como variável de ambiente e você chama `DynoLayer.configure(region="us-east-1")`, o valor `"us-east-1"` será usado.

### Opções disponíveis

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `region` | `AWS_REGION` ou `"sa-east-1"` | Região AWS |
| `endpoint_url` | `None` | URL customizada (LocalStack, DynamoDB Local) |
| `aws_access_key_id` | `None` | Chave de acesso AWS |
| `aws_secret_access_key` | `None` | Chave secreta AWS |
| `profile_name` | `None` | Nome do perfil AWS CLI |
| `timestamp_format` | `"numeric"` | `"numeric"` (unix int) ou `"iso"` (ISO 8601) |
| `timestamp_timezone` | `TIMESTAMP_TIMEZONE` ou `"America/Sao_Paulo"` | Timezone para timestamps |
| `retry_max_attempts` | `3` | Máximo de tentativas para retry |
| `retry_mode` | `"adaptive"` | Modo de retry: `"standard"` ou `"adaptive"` |

## Seu Primeiro Model

O DynoLayer segue o padrão Active Record, similar ao Eloquent do Laravel. Cada classe model representa uma tabela DynamoDB.

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",                           # Nome da tabela
            required_fields=["email", "name"],        # Campos obrigatórios
            fillable=["id", "email", "name", "role"], # Campos permitidos para mass assignment
            timestamps=True                           # Gerenciar created_at/updated_at
        )
```

### Parâmetros do Model

- **entity**: Nome da tabela DynamoDB
- **required_fields**: Campos que devem estar presentes ao criar registros
- **fillable**: Whitelist de campos que podem ser atribuídos em massa (proteção contra dados indesejados)
- **timestamps**: Quando `True`, adiciona automaticamente `created_at` e `updated_at`
- **timestamp_format**: Override do formato de timestamp para este model (`"numeric"` ou `"iso"`)

## Uso Básico

### Criar um registro

```python
# Usando o método create
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "role": "admin"
})

# Usando o método save
user = User()
user.id = 1
user.email = "john@example.com"
user.name = "John Doe"
user.role = "admin"
user.save()
```

### Criar em lote

```python
users = User.batch_create([
    {"id": 1, "email": "john@example.com", "name": "John", "role": "admin"},
    {"id": 2, "email": "jane@example.com", "name": "Jane", "role": "admin"},
])
```

### Buscar registros

```python
# Buscar todos
users = User.all().get()

# Buscar por chave primária
user = User.find({"id": 1})

# Buscar ou lançar exceção
user = User.find_or_fail({"id": 1}, "Usuário não encontrado")

# Buscar vários por chave primária (batch)
users = User.batch_find([{"id": 1}, {"id": 2}, {"id": 3}])
```

### Atualizar um registro

```python
user = User.find({"id": 1})
user.name = "Jane Doe"
user.save()
```

### Deletar um registro

```python
# Deletar instância
user = User.find({"id": 1})
user.delete()

# Ou usar o método destroy
User.destroy({"id": 1})

# Deletar em lote
User.batch_destroy([{"id": 1}, {"id": 2}, {"id": 3}])
```

## Próximos Passos

- Aprenda sobre o [Query Builder](query-builder.md) para filtros avançados
- Explore [Collections](collections.md) para trabalhar com conjuntos de resultados
- Veja [Advanced Features](advanced.md) para configuração avançada, paginação, timestamps e mais