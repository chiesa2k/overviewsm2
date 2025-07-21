import pandas as pd
import sqlite3
import os

# --- CONFIGURAÇÃO ---
nome_banco_dados = "gerenciamento.db"
arquivos_csv = {
    "gerenciamento_para_db.csv": "Vendas",
}

# --- FUNÇÃO DE LIMPEZA DE MOEDA ---
def limpar_valor_monetario_final(valor):
    if not isinstance(valor, str):
        return float(valor) if pd.notna(valor) else 0.0
    valor_limpo = valor.replace('R$', '').strip()
    if not valor_limpo or valor_limpo == '-':
        return 0.0
    valor_limpo = valor_limpo.replace(',', '')
    try:
        return float(valor_limpo)
    except (ValueError, TypeError):
        return 0.0

# --- LÓGICA DE MIGRAÇÃO ---
def migrar_dados():
    if os.path.exists(nome_banco_dados):
        print(f"Aviso: O banco de dados '{nome_banco_dados}' já existe e será substituído.")
        os.remove(nome_banco_dados)

    print(f"Criando o novo banco de dados '{nome_banco_dados}'...")
    conexao = sqlite3.connect(nome_banco_dados)

    try:
        for nome_arquivo, nome_tabela in arquivos_csv.items():
            print(f"Lendo dados de '{nome_arquivo}'...")
            df = pd.read_csv(nome_arquivo, encoding='latin-1')
            
            df.columns = df.columns.str.strip()
            print("Nomes das colunas limpos.")

            # --- ATUALIZAÇÃO: Limpando as DUAS colunas de data ---
            colunas_de_data = ["DATA (FATURAMENTO)", "DATA (RECEBIMENTO PO)"]
            for coluna in colunas_de_data:
                if coluna in df.columns:
                    print(f"Convertendo a coluna de data '{coluna}'...")
                    df[coluna] = pd.to_datetime(df[coluna], dayfirst=True, errors='coerce')
            
            coluna_valor = "VALOR - VENDA (TOTAL) DESC."
            if coluna_valor in df.columns:
                print(f"Limpando e convertendo a coluna de valor '{coluna_valor}'...")
                df[coluna_valor] = df[coluna_valor].apply(limpar_valor_monetario_final)
                print("Conversão de valor monetário finalizada.")

            print(f"Salvando dados na tabela '{nome_tabela}'...")
            df.to_sql(nome_tabela, conexao, index=False, if_exists='replace')
            print(f"-> Sucesso! Tabela '{nome_tabela}' criada com {len(df)} linhas.")

        print("\n🎉 Migração final (com todas as limpezas) concluída!")

    except Exception as e:
        print(f"\nOcorreu um erro durante a migração: {e}")
    finally:
        conexao.close()

if __name__ == "__main__":
    migrar_dados()