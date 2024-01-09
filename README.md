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

Para iniciar, primeiro você precisa criar a sua model herdando a classe *DynoLayer*. O nome da tabela e os atributos obrigatórios são os únicos campos requeridos, os demais já possuem um valor padrão.

```python
from dynolayer import DynoLayer


class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__('users', [])
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
Para os casos de consultas com filtro em determinada propriedade que não seja uma chave de partição, pode-se usar o método **find_by**. Para verificar a contagem de itens recebidos ao realizar o fetch (após o *find* ou *find_by*), basta usar a propriedade **count**

```python
users = User()
online_users = users.find_by('status', 'online').fetch(True)
print(f'{users.count} online no momento!')
```

### Destroy

Para remover um registro, basta obter a sua chave de partição e executar o método **destroy()** em seguida.

```python
user = User().find_by_id('meu-id-55')

if user.destroy():
    print('Usuário removido com sucesso!')
```
