# Changelog

Todas as mudanças relevantes do DynoLayer serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
