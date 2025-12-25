from setuptools import setup

with open('README.md', 'r') as file:
    readme = file.read()

setup(
    name='dynolayer',
    version='0.6.1',
    license='MIT License',
    packages=['dynolayer'],
    install_requires=['pytz'],
    extras_require={"aws": ["boto3"]},
    keywords=['dynolayer', 'dynamodb', 'active record', 'aws lambda'],
    author='Kauê Leal de Lima',
    author_email='kaueslim@gmail.com',
    description='O DynoLayer é uma ferramenta poderosa que simplifica e agiliza o acesso e manipulação de dados no Amazon DynamoDB, baseada no padrão Active Record.',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/kauelima21/dynolayer',
)
