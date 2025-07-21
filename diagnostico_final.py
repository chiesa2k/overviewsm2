import pandas as pd

# O nome do seu arquivo CSV
NOME_ARQUIVO_CSV = "gerenciamento_para_db.csv"
# O nome exato da coluna de valor, sem os espaços extras
NOME_COLUNA_VALOR = "VALOR - VENDA (TOTAL) DESC."

def limpar_valor_monetario_robusto(valor):
    if not isinstance(valor, str):
        return float(valor) if pd.notna(valor) else 0.0
    valor_limpo = valor.replace('R$', '').strip()
    valor_limpo = valor_limpo.replace('.', '')
    valor_limpo = valor_limpo.replace(',', '.')
    try:
        return float(valor_limpo)
    except (ValueError, TypeError):
        return 0.0

try:
    print(f"--- Lendo o arquivo: {NOME_ARQUIVO_CSV} ---")
    df = pd.read_csv(NOME_ARQUIVO_CSV, encoding='latin-1')
    
    # Limpa os nomes das colunas (remove espaços do início/fim)
    df.columns = df.columns.str.strip()

    # Cria uma nova coluna com o valor limpo para podermos comparar
    df['VALOR_LIMPO'] = df[NOME_COLUNA_VALOR].apply(limpar_valor_monetario_robusto)

    print("\n--- COMPARANDO OS VALORES (15 primeiras linhas) ---")
    print("Mostrando a coluna original e a coluna após a limpeza:\n")
    print(df[[NOME_COLUNA_VALOR, 'VALOR_LIMPO']].head(15).to_string())

    # Calcula a soma da nova coluna limpa
    soma_total_limpa = df['VALOR_LIMPO'].sum()
    print("\n--- SOMA FINAL ---")
    print(f"A soma total da coluna 'VALOR_LIMPO' é: {soma_total_limpa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

except FileNotFoundError:
    print(f"ERRO: O arquivo '{NOME_ARQUIVO_CSV}' não foi encontrado. Verifique se ele está na mesma pasta.")
except KeyError:
    print(f"ERRO: A coluna '{NOME_COLUNA_VALOR}' não foi encontrada no arquivo. Verifique o nome exato da coluna.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")