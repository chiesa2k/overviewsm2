import sqlite3

NOME_BANCO_DADOS = "gerenciamento.db"
NOME_TABELA = "Vendas"

try:
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    # Este comando especial pede ao SQLite as informações da tabela
    cursor.execute(f"PRAGMA table_info('{NOME_TABELA}');")
    colunas = [row[1] for row in cursor.fetchall()]
    conexao.close()

    print(f"✅ As colunas na tabela '{NOME_TABELA}' são:")
    print(colunas)

except Exception as e:
    print(f"Ocorreu um erro: {e}")