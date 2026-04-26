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
| `timestamp_format` | `"iso"` | `"numeric"` (unix int) ou `"iso"` (ISO 8601) |
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
            timestamps=True,
            partition_key="id",
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
            timestamp_format="numeric",  # Apenas este model usa NUMERIC
            partition_key="id",
        )

class Metrics(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="metrics",
            fillable=["id", "value", "metric_name"],
            timestamps=True,
            partition_key="id",
            # Usa o formato da configuração global (padrão: "iso")
        )
```

### Exemplos

```python
# Com timestamp_format="iso" (padrão)
user = User.create({
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe"
})
print(user.created_at)  # "2026-04-05T14:30:00-03:00"
print(user.updated_at)  # "2026-04-05T14:30:00-03:00"

# Com timestamp_format="numeric"
log = Logs.create({
    "id": 1,
    "message": "User logged in",
    "level": "info"
})
print(log.created_at)  # 1735132800
print(log.updated_at)  # 1735132800
```

### Timezone

O timezone padrão é `America/Sao_Paulo`. Para alterar:

```python
# Via configuração
DynoLayer.configure(timestamp_timezone="UTC")

# Ou via variável de ambiente
# export TIMESTAMP_TIMEZONE=UTC
```

## Auto-ID

O DynoLayer pode gerar IDs automaticamente para a partition key do seu model. A configuração é por model — cada tabela pode usar uma estratégia diferente.

### Estratégias disponíveis

| Estratégia | Tipo | Descrição |
|-----------|------|-----------|
| `"uuid4"` | `str` | UUID v4 aleatório (recomendado) |
| `"uuid1"` | `str` | UUID v1 (time-based + MAC address) |
| `"uuid7"` | `str` | UUID v7 time-ordered (Python 3.14+, fallback para uuid4) |
| `"numeric"` | `int` | Inteiro incremental via tabela de sequências |

### UUID

```python
class Product(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="products",
            required_fields=["name"],
            fillable=["id", "name", "price"],
            auto_id="uuid4",
            partition_key="id",
        )


product = Product.create({"name": "Widget"})
print(product.id)  # "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
```

### UUID truncado

Use `auto_id_length` para gerar IDs mais curtos (mínimo 16, máximo 32 caracteres hex):

```python
class Product(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="products",
            fillable=["id", "name"],
            auto_id="uuid4",
            auto_id_length=16,  # 16 caracteres hex
            partition_key="id",
        )


product = Product.create({"name": "Widget"})
print(product.id)  # "a1b2c3d4e5f64a7b"
```

### Numérico incremental

Usa uma tabela DynamoDB auxiliar com contadores atômicos, similar a sequences do PostgreSQL. Seguro para execuções concorrentes (ex: múltiplas Lambdas).

#### Setup da tabela de sequências

Crie a tabela de sequências no DynamoDB (via console, CloudFormation, SAM, etc):

```
Table name: dynolayer_sequences  (ou nome customizado)
Partition key: entity (String)
```

#### Uso

```python
class Order(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="orders",
            required_fields=["total"],
            fillable=["id", "total", "status"],
            auto_id="numeric",
            partition_key="id",
        )


order1 = Order.create({"total": 100, "status": "pending"})
order2 = Order.create({"total": 200, "status": "pending"})
print(order1.id)  # 1
print(order2.id)  # 2
```

#### Tabela de sequências customizada

Por model:

```python
class Order(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="orders",
            fillable=["id", "total"],
            auto_id="numeric",
            auto_id_table="my_sequences",  # Override por model
            partition_key="id",
        )
```

Ou globalmente:

```python
DynoLayer.configure(auto_id_table="my_sequences")
```

### Comportamento

- O ID é gerado **apenas quando a partition key não está presente** nos dados. Se você fornecer um ID explícito, ele será usado.
- Funciona com `create()`, `batch_create()` e `save()`.
- Em `batch_create()` com estratégia `numeric`, os IDs são gerados em uma única chamada atômica ao DynamoDB para melhor performance.

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

## create() vs save()

O DynoLayer oferece dois caminhos para criar registros:

| Método | Operação DynamoDB | Comportamento |
|--------|------------------|---------------|
| `create()` | PutItem | Substitui o item inteiro. Ideal para novos registros. |
| `save()` | UpdateItem | Upsert — cria se não existe, atualiza campos específicos se existe. |

```python
# create() — PutItem: sempre substitui o item inteiro
user = User.create({"id": 1, "email": "john@example.com", "name": "John"})

# save() — UpdateItem: atualiza apenas os campos definidos
user = User()
user.id = 1
user.email = "john@example.com"
user.save()  # Cria se não existe, atualiza se existe
```

### Escrita condicional (unique create)

Use `unique=True` para garantir que o `create()` não sobrescreva um registro existente:

```python
from dynolayer.exceptions import ConditionalCheckException

try:
    user = User.create({"id": 1, "email": "john@example.com", "name": "John"}, unique=True)
except ConditionalCheckException:
    print("Registro com id=1 já existe!")
```

### Condição no save()

Passe uma condição boto3 para `save()` para escrita condicional:

```python
from boto3.dynamodb.conditions import Attr

user = User.find({"id": 1})
user.name = "Jane"

# Só atualiza se o role for "admin"
user.save(condition=Attr("role").eq("admin"))
```

## Transações

O DynoLayer suporta transações atômicas do DynamoDB (até 25 operações por transação, all-or-nothing).

### Escrita transacional

```python
from dynolayer import DynoLayer

DynoLayer.transact_write([
    User.prepare_put({"id": 1, "email": "john@example.com", "name": "John"}),
    Order.prepare_put({"id": 100, "user_id": 1, "total": 50}),
    CartItem.prepare_delete({"id": 1}),
])
```

### Helpers disponíveis

| Helper | Descrição |
|--------|-----------|
| `prepare_put(data)` | Prepara inserção (aplica fillable, auto_id, timestamps) |
| `prepare_delete(key)` | Prepara deleção por chave |
| `prepare_update(key, data)` | Prepara atualização de campos específicos |

### Leitura transacional

```python
results = DynoLayer.transact_get([
    (User, {"id": 1}),
    (Order, {"id": 100}),
])

user = results[0]   # Instância de User (ou None)
order = results[1]  # Instância de Order (ou None)
```

## Paginação

O DynamoDB retorna resultados em páginas (até 1MB por página). O DynoLayer oferece suporte a paginação automática e manual.

### Paginação automática

Use `paginate=True` para percorrer todas as páginas automaticamente. Combine com `all=True` para obter a `Collection` completa:

```python
# Buscar todos os registros de todas as páginas
all_users = User.all().get(all=True, paginate=True)
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

# Executar query (all=True → Collection, sem seguir páginas)
results = query.fetch(all=True)

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
            fillable=["id", "email", "name"],
            partition_key="id",
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
            timestamps=True,
            partition_key="id",
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
            fillable=["id", "email", "name", "role"],
            partition_key="id",
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
            fillable=["id", "email", "name"],  # Apenas estes podem ser atribuídos
            partition_key="id",
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

## Otimização para Lambda

O parâmetro `partition_key` (padrão: `"id"`) e `sort_key` (quando aplicável) permitem que o DynoLayer funcione sem chamar `describe_table` no init, eliminando uma API call extra que adicionaria latência no cold start em AWS Lambda. Se a partition key da sua tabela é `"id"`, não é necessário declarar o parâmetro.

```python
# partition_key="id" é o padrão — não precisa declarar
class User(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="users",
            fillable=["id", "email", "name"],
        )

# Para tabelas com partition key diferente, declare explicitamente
class Event(DynoLayer):
    def __init__(self):
        super().__init__(
            entity="events",
            fillable=["user_id", "timestamp", "type", "payload"],
            partition_key="user_id",
            sort_key="timestamp",
        )
```

Com as chaves declaradas:
- `create()`, `find()`, `save()`, `delete()` funcionam **sem nenhuma API call ao DynamoDB no init**
- Índices secundários são carregados **lazy** — apenas quando `.index()` é chamado pela primeira vez
- Se o model não usa `.index()`, o `describe_table` nunca é chamado

### Projeção no find

Busque apenas os campos necessários para reduzir transferência de dados:

```python
# Busca apenas name e email (menor payload)
user = User.find({"id": 1}, attributes=["name", "email"])
```

### Streaming para tabelas grandes

Use `stream()` em vez de `get(all=True, paginate=True)` para processar tabelas grandes sem carregar tudo em memória. Isso previne OOM em Lambda (128MB default):

```python
# Ruim — carrega todos os registros em memória
all_users = User.all().get(all=True, paginate=True)

# Bom — processa um por um, página por página
for user in User.all().stream():
    process(user)

# Também funciona com filtros
for user in User.where("role", "admin").index("role-index").stream():
    send_notification(user)
```

## Acesso a Campos via Dicionário

O DynoLayer usa `__getattr__`/`__setattr__` para expor campos do DynamoDB como propriedades do objeto. Isso funciona na maioria dos casos, mas causa colisão quando o nome de um campo coincide com um método da classe.

### O problema

```python
user = User.find({"id": 1})
user.data       # → <bound method DynoLayer.data>  (método, não o campo!)
user.data()     # → {"id": 1, "data": "valor real", ...}
```

O Python resolve métodos definidos na classe **antes** de chamar `__getattr__`, então campos com nomes como `data`, `save`, `get`, `count`, `index`, `limit`, `stream`, `offset`, entre outros, ficam inacessíveis via acesso direto por atributo.

### A solução: sintaxe de dicionário

Use `item["key"]` para acessar qualquer campo de forma segura:

```python
user = User.find({"id": 1})

# Acesso seguro — nunca colide com métodos
user["data"]           # → valor do campo "data"
user["save"]           # → valor do campo "save"

# Atribuição
user["name"] = "Ana"   # Equivalente a user.name = "Ana"

# Verificar existência
if "email" in user:
    print(user["email"])

# Deletar campo
del user["role"]
```

### Quando usar cada sintaxe

| Sintaxe | Quando usar |
|---------|-------------|
| `user.name` | Campos com nomes que **não** colidem com métodos da classe |
| `user["name"]` | Sempre seguro — especialmente quando o nome do campo é dinâmico ou pode colidir |

Para código defensivo ou quando os nomes dos campos vêm de input externo, prefira sempre a sintaxe de dicionário.

## Modo Silencioso (raise_on_error)

A partir da v2.0 o DynoLayer opera em modo silencioso por padrão (`raise_on_error = False`): as exceções são suprimidas e os métodos retornam indicadores de falha. O erro fica acessível via `fail()`. Para reativar o comportamento estrito (v1.x), defina `raise_on_error = True` no seu model.

### Reativando exceções (comportamento v1.x)

```python
class User(DynoLayer):
    raise_on_error = True

    def __init__(self):
        super().__init__(
            entity="users",
            required_fields=["email", "name"],
            fillable=["id", "email", "name", "role"],
            partition_key="id",
        )
```

### Retornos em modo silencioso

Quando `raise_on_error = False` (default), cada método retorna um valor indicando falha em vez de lançar exceção:

| Método | Retorno em caso de erro |
|--------|------------------------|
| `get_item()` | `None` |
| `create()` | `None` |
| `delete()` | `False` |
| `find_or_fail()` | `None` |
| `batch_create()` | `[]` |
| `batch_find()` | `Collection([])` |
| `batch_destroy()` | `False` |
| `save()` | `False` |
| `destroy()` | `False` |
| `get()` | `Collection([])` |
| `count()` | `0` |

### Acessando o erro com fail()

O método `fail()` retorna a última exceção capturada (`DynoLayerException` ou subclasse), ou `None` se não houver erro. Funciona tanto na classe quanto na instância:

```python
# Usando como class method
user = User.get_item({})
if user is None:
    error = User.fail()
    print(f"Erro: {error}")  # Ex: ValidationException

# Usando como instance method
user = User()
user.email = "invalid"
result = user.save()
if result is False:
    error = user.fail()
    print(f"Erro: {error}")
```

> **Nota**: O `fail()` é resetado automaticamente a cada nova operação. Consulte-o logo após a operação que deseja verificar.

### Quando usar

O modo silencioso é útil quando você quer tratar erros sem try/except, por exemplo em pipelines de processamento em lote onde uma falha individual não deve interromper o fluxo:

```python
for data in batch:
    result = User.create(data)
    if result is None:
        logger.warning(f"Falha ao criar usuário: {User.fail()}")
        continue
    process(result)
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
users = User.where("role", "admin").get(all=True, paginate=True)
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
