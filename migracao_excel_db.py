import pandas as pd
import sqlite3
import os

# --- CONFIGURAÇÃO ---
NOME_BANCO_DADOS = "gerenciamento.db"
NOME_ARQUIVO_EXCEL = "SM_Gerenciamento_19_20 (6).xlsx" 
NOME_DA_ABA = "Gerenciamento"

# --- FUNÇÃO DE LIMPEZA DE MOEDA ---
def limpar_valor_monetario(valor):
    if not isinstance(valor, str):
        return float(valor) if pd.notna(valor) else 0.0
    valor_limpo = valor.replace('R$', '').strip()
    if not valor_limpo or valor_limpo == '-':
        return 0.0
    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
    try:
        return float(valor_limpo)
    except (ValueError, TypeError):
        return 0.0

# --- LÓGICA DE MIGRAÇÃO ---
def migrar_dados():
    if not os.path.exists(NOME_ARQUIVO_EXCEL):
        print(f"ERRO: Arquivo '{NOME_ARQUIVO_EXCEL}' nao encontrado.")
        return

    if os.path.exists(NOME_BANCO_DADOS):
        print(f"Aviso: O banco de dados '{NOME_BANCO_DADOS}' ja existe e sera substituido.")
        os.remove(NOME_BANCO_DADOS)

    print(f"Criando o novo banco de dados '{NOME_BANCO_DADOS}'...")
    conexao = sqlite3.connect(NOME_BANCO_DADOS)

    try:
        print(f"Lendo a aba '{NOME_DA_ABA}' do arquivo '{NOME_ARQUIVO_EXCEL}'...")
        df = pd.read_excel(NOME_ARQUIVO_EXCEL, sheet_name=NOME_DA_ABA, engine='openpyxl')
        
        df.columns = df.columns.str.strip()
        print("Nomes das colunas limpos.")

        colunas_de_data = ["DATA (FATURAMENTO)", "DATA (RECEBIMENTO PO)", "DATA (ENVIO DOS RELATÓRIOS)", "DATA (FINAL ATENDIMENTO)"]
        for coluna in colunas_de_data:
            if coluna in df.columns:
                print(f"Convertendo a coluna de data '{coluna}'...")
                df[coluna] = pd.to_datetime(df[coluna], errors='coerce')
        
        coluna_valor = "VALOR - VENDA (TOTAL) DESC."
        if coluna_valor in df.columns:
            print(f"Limpando e convertendo a coluna de valor '{coluna_valor}'...")
            df[coluna_valor] = df[coluna_valor].apply(limpar_valor_monetario)
            print("Conversao de valor monetario finalizada.")

        print(f"Salvando dados na tabela 'Vendas'...")
        df.to_sql("Vendas", conexao, index=False, if_exists='replace')
        print(f"-> Sucesso! Tabela 'Vendas' criada com {len(df)} linhas.")

        # --- EMOJI REMOVIDO DAQUI ---
        print("\nMigracao final (lendo do Excel) concluida!")

    except Exception as e:
        print(f"\nOcorreu um erro durante a migracao: {e}")
    finally:
        conexao.close()

if __name__ == "__main__":
    migrar_dados()