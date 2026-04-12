# Spec: Método `find` — Query & Scan Unificado

**Versão:** 1.3.0  
**Status:** Proposta  
**Data:** 2026-04-12

---

## Motivação

Hoje, para fazer query/scan no dynolayer, é necessário encadear múltiplas chamadas:

```python
Address().and_where("user_id", user_id).index("user-index").fetch(True)
```

O objetivo é oferecer uma API mais expressiva e concisa com um único método `find`, que aceita uma expression string com placeholders e valores via kwargs:

```python
Address().find("user_id = :uid", uid=user_id).index("user-index").fetch(True)
```

---

## Breaking Changes

### `find(dict)` → `get_item(dict)`

O método `find` atual (classmethod que faz `get_item` por chave primária) será renomeado para `get_item`.

```python
# Antes (v1.x)
Address.find({"user_id": "123"})
Address.find({"user_id": "123"}, attributes=["name", "city"])

# Depois (v1.3.0)
Address.get_item({"user_id": "123"})
Address.get_item({"user_id": "123"}, attributes=["name", "city"])
```

### `find_or_fail`

Passa a chamar `get_item` internamente. A assinatura pública não muda.

### `find` deixa de ser classmethod

O novo `find` é método de instância, exigindo `()` na classe:

```python
# Antes
Address.find({"pk": "1"})

# Depois
Address().find("pk = :val", val="1").fetch()
```

---

## API Pública

### `get_item(key, attributes=None)` — classmethod

Substitui o `find(dict)` antigo. Busca um item por chave primária exata via `GetItem`.

```python
@classmethod
def get_item(cls, key: dict, attributes: List[str] = None) -> Optional[DynoLayer]
```

**Exemplos:**

```python
user = User.get_item({"user_id": "123"})
user = User.get_item({"user_id": "123"}, attributes=["name", "email"])
```

---

### `find(expression=None, /, **values)` — método de instância

Método unificado para query e scan. Retorna `self` para chaining.

```python
def find(self, expression: str = None, /, **values) -> DynoLayer
```

**Comportamento:**

| Chamada | Ação |
|---|---|
| `find()` | Scan geral (equivale ao `all()` atual) |
| `find("attr = :val", val=x)` | Auto-detecta: query se `attr` é partition key, scan com filter caso contrário |
| `find("attr = :val", val=x).index("gsi")` | Query no GSI se `attr` é key do index, senão filter no scan |

**Fluxo interno:**
1. Se `expression` é `None` → seta `_scan_all = True`, retorna `self`
2. Parseia a expression → lista de `(operador_lógico, atributo, condição, valor)`
3. Para cada condição, chama `__set_filter_expression` (que auto-detecta key vs filter)
4. Retorna `self` para chaining com `.index()`, `.limit()`, `.offset()`, `.fetch()`, etc.

---

## Sintaxe da Expression

### Formato geral

```
atributo operador :placeholder [CONECTOR atributo operador :placeholder ...]
```

Os `:placeholder` são mapeados para os `**kwargs` pelo nome (sem os dois pontos).

---

### Operadores de condição

Todos os operadores já suportados pelo query builder são aceitos na expression:

#### Key condition + Filter

| Operador | Sintaxe | Exemplo |
|---|---|---|
| Igual | `attr = :val` | `"user_id = :uid"` |
| Menor que | `attr < :val` | `"age < :max"` |
| Menor ou igual | `attr <= :val` | `"age <= :max"` |
| Maior que | `attr > :val` | `"age > :min"` |
| Maior ou igual | `attr >= :val` | `"age >= :min"` |
| Começa com | `attr begins_with :val` | `"name begins_with :prefix"` |
| Entre | `attr between :start and :end` | `"age between :min and :max"` |

#### Somente Filter (não válidos como key condition)

| Operador | Sintaxe | Exemplo |
|---|---|---|
| Diferente | `attr <> :val` | `"status <> :s"` |
| Contém | `attr contains :val` | `"tags contains :tag"` |
| Está em | `attr in :val` | `"status in :list"` (valor deve ser lista) |
| Existe | `attr exists` | `"email exists"` (sem placeholder) |
| Não existe | `attr not_exists` | `"phone not_exists"` (sem placeholder) |
| Tipo do atributo | `attr attribute_type :val` | `"data attribute_type :t"` |

---

### Conectores lógicos

Usados para combinar múltiplas condições:

| Conector | Equivalente atual | Exemplo |
|---|---|---|
| `AND` | `and_where()` | `"user_id = :uid AND status = :s"` |
| `OR` | `or_where()` | `"city = :c1 OR city = :c2"` |
| `AND NOT` | `where_not()` | `"user_id = :uid AND NOT status = :s"` |
| `OR NOT` | `or_where_not()` | `"user_id = :uid OR NOT archived = :a"` |

A primeira condição é sempre tratada como `AND` (condição base).

> **Nota:** O `and` dentro de `between :start and :end` é parte do operador `between`, não um conector lógico. O parser trata isso automaticamente.

---

## Exemplos Completos

### Scan geral

```python
# Todos os registros
addresses = Address().find().fetch(True)
```

### Query por partition key

```python
# Auto-detecta que user_id é partition key → executa Query
addresses = Address().find("user_id = :uid", uid="123").fetch(True)
```

### Query em GSI

```python
# Query no Global Secondary Index
addresses = Address().find("city = :c", c="São Paulo").index("city-index").fetch(True)
```

### Scan com filter

```python
# city não é key da tabela → executa Scan com FilterExpression
addresses = Address().find("city = :c", c="São Paulo").fetch(True)
```

### Múltiplas condições (AND)

```python
addresses = Address().find(
    "user_id = :uid AND status = :s",
    uid="123",
    s="active"
).fetch(True)
```

### OR

```python
addresses = Address().find(
    "city = :c1 OR city = :c2",
    c1="São Paulo",
    c2="Rio de Janeiro"
).fetch(True)
```

### AND NOT

```python
addresses = Address().find(
    "user_id = :uid AND NOT status = :s",
    uid="123",
    s="deleted"
).fetch(True)
```

### OR NOT

```python
addresses = Address().find(
    "user_id = :uid OR NOT archived = :a",
    uid="123",
    a=True
).fetch(True)
```

### Between

```python
orders = Order().find(
    "created_at between :start and :end",
    start="2024-01-01",
    end="2024-12-31"
).fetch(True)
```

### Begins with

```python
users = User().find("name begins_with :prefix", prefix="Jo").fetch(True)
```

### Contains

```python
posts = Post().find("tags contains :tag", tag="python").fetch(True)
```

### In (valor deve ser lista)

```python
users = User().find("status in :statuses", statuses=["active", "pending"]).fetch(True)
```

### Exists / Not exists

```python
# Sem placeholder — não precisa de kwargs
users = User().find("email exists").fetch(True)
users = User().find("phone not_exists").fetch(True)
```

### Combinações complexas

```python
addresses = Address().find(
    "user_id = :uid AND email exists AND NOT status = :s",
    uid="123",
    s="deleted"
).index("user-index").limit(50).fetch(True)
```

### Com paginação

```python
page1 = Address().find("user_id = :uid", uid="123").limit(10).fetch()
last_key = page1.last_evaluated_key  # via instância que executou

page2 = Address().find("user_id = :uid", uid="123").limit(10).offset(last_key).fetch()
```

---

## Parser de Expressions

### Nova função: `parse_expression(expression, **values)`

**Localização:** `dynolayer/utils.py`

**Entrada:**
- `expression`: string com a expression (ex: `"user_id = :uid AND status = :s"`)
- `**values`: kwargs com os valores dos placeholders

**Saída:**
Lista de tuplas: `(operador_lógico, atributo, operador_condição, valor)`

**Algoritmo:**
1. Tokenizar a expression, identificando primeiro padrões `between :x and :y` para proteger o `and` interno
2. Split pelos conectores lógicos (`AND NOT`, `OR NOT`, `AND`, `OR`) — nesta ordem de prioridade para evitar ambiguidade
3. Para cada fragmento, extrair via regex: `atributo`, `operador`, `:placeholder(s)`
4. Resolver placeholders → valores dos kwargs
5. Validar que todos os placeholders foram fornecidos

**Erros:**
- `InvalidArgumentException` se um placeholder não tem valor correspondente nos kwargs
- `InvalidArgumentException` se a expression tem sintaxe inválida
- `InvalidArgumentException` se `in` recebe valor que não é lista

---

## Alterações por Arquivo

### `dynolayer/utils.py`

- **Nova função:** `parse_expression(expression: str, **values) -> List[Tuple[str, str, str, Any]]`

### `dynolayer/dynolayer.py`

- **Novo classmethod:** `get_item(cls, key: dict, attributes: List[str] = None) -> Optional[DynoLayer]` — código do `find` atual
- **Novo método de instância:** `find(self, expression: str = None, /, **values) -> DynoLayer`
- **Alteração:** `find_or_fail` passa a chamar `get_item` em vez de `find`
- **Remoção:** `find` classmethod antigo (substituído por `get_item`)

### `dynolayer/__init__.py`

- Exportar `get_item` se necessário

### `tests/`

- Testes para `get_item` (migração dos testes de `find(dict)` existentes)
- Testes para `find()` sem args (scan all)
- Testes para `find(expression)` com cada operador de condição
- Testes para `find(expression)` com cada conector lógico
- Testes para `find().index()` (query em GSI)
- Testes para `parse_expression` (unit tests do parser)
- Testes de erro: placeholder faltando, sintaxe inválida, `in` sem lista

### `CHANGELOG.md`

- Entrada para v1.3.0 com breaking changes documentados