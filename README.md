# DynoLayer

O **DynoLayer** é uma ferramenta poderosa que simplifica e agiliza o acesso e manipulação de dados no Amazon DynamoDB. Baseada no padrão Active Record, esta biblioteca oferece uma abstração intuitiva para interagir com tabelas no DynamoDB, permitindo operações de CRUD (Create, Read, Update, Delete) de forma fácil e natural.

## Instalação

Para usar o pacote basta instalar através do gerenciador de dependências de sua preferência.

```sh
pip install dynolayer
```

ou

```sh
pipenv install dynolayer
```

## Exemplos

Para mais exemplos, consulte a pasta [docs](https://github.com/kauelima21/dynolayer/tree/main/docs)

Para iniciar, primeiro você precisa criar a sua model herdando a classe *DynoLayer*. O nome da tabela e os atributos obrigatórios são os únicos campos requeridos, os demais já possuem um valor padrão.

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__('users', [])
```

Por padrão, o timezone utilizado é o ```America/Sao_Paulo```. Para alterar isso basta adicionar a variável de ambiente **TIMESTAMP_TIMEZONE** com o valor desejado.

```sh
TIMESTAMP_TIMEZONE='US/Eastern'
```

O mesmo se aplica para a região e para o uso local do dynamodb. Caso as variáveis abaixo não existam, os valores padrão serão **sa-east-1** e o dynamodb da da aws na região utilizada.

```sh
REGION='us-east-1'
LOCAL_ENDPOINT='http://localhost:8000'
```

### Save

Para criar um registro, é preciso instanciar a model e atribuir valor as suas propriedades. Depois basta rodar um **save()** para salvar no banco!

```python
user = User()

user.full_name = 'John Doe'
user.email = 'john@mail.com'
user.stars = 5
user.phones = [
    '11 91234-5678',
    '10 95678-1234',
]

if user.save():
    print('Usuário adicionado com sucesso!')
```

O mesmo método é usado para atualizar o registro, basta possuir a chave de partição e os dados que precisam ser alterados.

```python
user = User()

user.id = 'meu-id-55'
user.email = 'john.doe@email.com' # altera o email

user.save() # atualiza o registro para o novo email
```

### Find By Id

Para buscar um registro pela chave de partição, se usa o método **find_by_id()**. O mesmo vai retornar a instancia da model com os atributos buscados, mantendo o Active Record e possibilitando a execução de outras instruções, como o update que vimos a pouco.

```python
user = User().find_by_id('meu-id-55')
user.stars = 17
print(f'O usuário {user.full_name} possui {user.stars} estrelas!')

user.save()
```

### Find

Para as demais consultas, como uma busca geral (scan) ou uma busca com filtro, o método utilizado é o **find()** e os métodos subsequentes para formar um *Query Builder*.

```python
# busca todos os produtos
products = Product().find().fetch() 

# busca todos os usuários que estão com o status COMPLETED
completed_users = User().find(
    '#st = :st',
    {':st': 'COMPLETED'},
    {'#st': 'status'}
).fetch()

# busca todos os usuários com limite de 10
users = User().find().limit(10).fetch() 
```

É importante destacar que o scan possui um limite na quantidade de dados que retorna, e para trabalhar com isso basta assinalar o parâmetro *paginate_through_results* como ```True``` no método **fetch()**.

```python
# busca todos os produtos paginando o resultado da consulta no DynamoDB
products = Product().find().fetch(True)
```

### Find By
Para os casos de consultas com filtro em determinada propriedade que não seja uma chave de partição, pode-se usar o método **find_by**. Para verificar a contagem de itens recebidos ao realizar o fetch (após o *find* ou *find_by*), basta usar a propriedade **get_count**

```python
users = User()
online_users = users.find_by('status', 'online').fetch(True)
print(f'{users.get_count} online no momento!')
```

### Query By
Para os casos de consultas com filtro em determinada chave de partição, pode-se usar o método **query_by**.

```python
users = User()
online_users = users.query_by('status', 'online').fetch(True)
print(f'{users.get_count} online no momento!')
```

### Order
Serve para ordenar de acordo com determinado atributo, podendo também trazer a resposta de form crescente ou decrescente, a depender do valor que for passado no segundo argumento que por padrão é True e retorna de maneira crescente.

```python
users = User()
online_users = users.find_by('status', 'online').order('first_name').fetch(True)
print(f'{users.get_count} online no momento!')
```

### Count
Caso queira contar o total de itens na tabela ou operação que você fizer sem retornar os dados registrados nela, basta substituir o método **fetch()** por **count()**

```python
users = User()
online_users = users.find_by('status', 'online').order('first_name').count()
print(f'{online_users} online no momento!')
```

### Fetch
Por default retorna os dados como um dict, mas ao passar o argumento object como True ele retorna os registros como um objeto DynoLayer.

```python
users = User().find_by('status', 'online').order('first_name').fetch(object=True)
print(users[0].name)
```

### Destroy

Para remover um registro, basta obter a sua chave de partição e executar o método **destroy()** em seguida.

```python
user = User().find_by_id('meu-id-55')

if user.destroy():
    print('Usuário removido com sucesso!')
```
