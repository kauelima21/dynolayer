## Paginação

Para implementar uma paginação usando o DynoLayer, deve-se obter primeiro as keys do último item recuperado da tabela. Com esse valor em mãos, podemos usar o método **offset()** para dizer ao DynoLayer que a consulta será executada a partir desse último resultado.

Exemplo:

```python
limit = 50
user = User()

total_count = user.find().count() # recupera todos os itens da tabela.

search = user.find().limit(limit) # consulta a ser realizada

# params: valor passado pelo client da api, podem ser as keys ou um NoneType. Varia da forma como a api foi construída.
last_evaluated_key = params.get('last_evaluated_key')
if (last_evaluated_key):
    search = search.offset(last_evaluated_key)

results = search.fetch()
results_count = user.get_count

api_response = {
    'total_count': total_count, # total de itens na tabela
    'results': results, # itens para apresentar
    'results_count': results_count, # total de itens para apresentar
    'last_evaluated_key': user.last_evaluated_key, # keys do ultimo registro recuperado
}
```
