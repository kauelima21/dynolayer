## Polimorfismo

Para usar polimorfismo com o DynoLayer, basta escrever o método dentro da classe modelo e modificar o seu comportamento.

Exemplo:

```python
from dynolayer import DynoLayer
from helpers import is_email_valid


# classe modelo
class User(DynoLayer):
    def __init__(self) -> None:
        super().__init__('users', [])

    # altera o método save conforme a necessidade (validação de e-mail) e invoca o método da classe Pai para executar a operação
    def save(self) -> bool:
        if not is_email_valid(self.email):
            return False
        return super().save()
```

Feito isso, basta instanciar a classe e executar o método.

```python
user = User()

user.email = 'invalid.com'
print(user.save()) # False

user.email = 'valid@mail.com'
print(user.save()) # True
```
