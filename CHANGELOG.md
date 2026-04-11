# Changelog

Todas as mudanças relevantes do DynoLayer serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.2.0] - 2026-04-11

### Added

- **Acesso via dicionário (`item["key"]`)**: Implementa `__getitem__`, `__setitem__`, `__contains__` e `__delitem__` na classe `DynoLayer`. Permite acessar campos do registro sem colisão com métodos internos como `data`, `save`, `get`, etc.

### Changed

- **Reordenação dos parâmetros do `__init__`**: Os parâmetros mais usados (`entity`, `required_fields`, `timestamps`, `partition_key`) agora vêm primeiro, seguidos dos menos comuns (`fillable`, `timestamp_format`, `auto_id`, `auto_id_length`, `auto_id_table`, `sort_key`).
- **Tipagem nos parâmetros `timestamp_format` e `auto_id`**: Agora usam `Literal` para autocomplete e validação estática.

## [1.1.0] - 2026-04-11

### Added

- **Modo silencioso (`raise_on_error`)**: Novo atributo de classe `raise_on_error = False` que suprime exceções em operações de leitura e escrita. Em vez de lançar exceções, os métodos retornam indicadores de falha (`None`, `False`, `Collection` vazia, `0`) e o erro fica acessível via `fail()`.
- **Método `fail()`**: Acessível tanto na instância (`user.fail()`) quanto na classe (`User.fail()`). Retorna a última exceção capturada (`DynoLayerException` ou subclasse), ou `None` se não houver erro. É resetado automaticamente a cada nova operação.

### Métodos afetados

| Método | Retorno em caso de erro |
|--------|------------------------|
| `find()` | `None` |
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

## [1.0.0] - 2026-04-10

### Breaking Changes

- **`partition_key` agora é obrigatório** na declaração do model. Elimina a chamada `describe_table` ao DynamoDB no init, removendo latência no cold start em Lambda.
- **`delete()` e `destroy()` tiveram os papéis trocados.** `delete(key)` agora é classmethod (deleta por chave), `destroy()` agora é método de instância (deleta o registro atual).

### Added

- **Auto-ID**: Geração automática de IDs por model via `auto_id`. Estratégias: `uuid4`, `uuid1`, `uuid7` e `numeric` (contadores atômicos via tabela de sequências).
- **Escrita condicional**: `create(data, unique=True)` previne sobrescrita de registros existentes. `save(condition=...)` aceita condições boto3 arbitrárias.
- **Transações**: `transact_write()` e `transact_get()` para operações atômicas com helpers `prepare_put()`, `prepare_delete()`, `prepare_update()`.
- **Validação de chaves primárias**: `find()`, `delete()`, `batch_find()` e `batch_destroy()` validam que todas as chaves primárias estão presentes antes de chamar o DynamoDB.
- **Validação de índices**: Verifica que o índice existe e que a partition key do índice está nas condições da query.
- **Resolução de key conditions**: Move automaticamente condições incompatíveis entre key condition e filter expression com base no índice alvo.
- **Projeção no find**: `find(key, attributes=["name", "email"])` busca apenas os campos solicitados.
- **`stream()`**: Generator que itera resultados página por página sem carregar tudo em memória, prevenindo OOM em tabelas grandes.
- **`where()` encadeável**: `User.where(...).where(...)` agora funciona corretamente, delegando para `and_where()` quando chamado em instância.
- **`sort_key` no model**: Declaração explícita da sort key para tabelas com chave composta.
- **`ConditionalCheckException`**: Wraps do erro DynamoDB para escrita condicional.
- **`AutoIdException`**: Exceção específica para falhas de geração de auto-ID.
- **Return type annotations**: Todos os métodos públicos agora possuem anotações de tipo de retorno.

### Improved

- **Cache do Table resource**: `boto3.Table()` agora é cacheado por entity, evitando alocação repetida de objetos.
- **Placeholders seguros**: `_update` e `prepare_update` sanitizam nomes de atributos com caracteres especiais nos placeholders do DynamoDB.
- **Distinção hash/sort key**: `_hash_key` e `_range_key` disponíveis separadamente para validações mais precisas.
- **Índices como dict estruturado**: `_indexes` agora armazena `hash_key` e `range_key` por índice em vez de lista flat.
- **Lazy loading de índices**: Índices secundários são carregados apenas quando `.index()` é usado pela primeira vez.

## [0.8.0] - 2026-04-05

### Added

- Paginação automática e manual
- Custom exceptions (`QueryException`, `ValidationException`, `RecordNotFoundException`, `InvalidArgumentException`)
