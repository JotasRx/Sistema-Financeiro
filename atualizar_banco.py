import sqlite3

conn = sqlite3.connect('banco.db')

# CUIDADO: Isso apagará os logins de teste que você já criou para gerar a nova estrutura
conn.execute('DROP TABLE IF EXISTS usuarios')

conn.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT,
        cpf_cnpj TEXT UNIQUE NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("Tabela de usuários atualizada com sucesso! Você já pode usar CPF/CNPJ.")
