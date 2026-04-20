from setuptools import setup

with open('README.md', 'r') as file:
    readme = file.read()

setup(
    name='dynolayer',
    version='2.0.0',
    license='MIT License',
    packages=['dynolayer'],
    install_requires=[],
    python_requires='>=3.9',
    extras_require={"full": ["boto3"]},
    keywords=['dynolayer', 'dynamodb', 'active record', 'aws lambda'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    author='Kauê Leal de Lima',
    author_email='kaueslim@gmail.com',
    description='O DynoLayer é uma ferramenta poderosa que simplifica e agiliza o acesso e manipulação de dados no Amazon DynamoDB, baseada no padrão Active Record.',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/kauelima21/dynolayer',
)
