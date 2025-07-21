import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO ---
NOME_BANCO_DADOS = "gerenciamento.db"
ANO_DE_ANALISE = 2025
MES_ATUAL = 7 # Julho

# --- FUNÇÕES DE CÁLCULO (Exatamente as mesmas do agente) ---

def executar_consulta(query: str) -> pd.DataFrame:
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    try:
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        print(f"!!! Erro na consulta SQL: {e}")
        return pd.DataFrame()
    finally:
        conexao.close()
    return df

def get_dados_mensais(df: pd.DataFrame, coluna_data: str, tipo_agregacao: str = 'valor') -> dict:
    if df.empty or coluna_data not in df.columns:
        return {i: 0 for i in range(1, 13)}
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df.dropna(subset=[coluna_data], inplace=True)
    if df.empty:
        return {i: 0 for i in range(1, 13)}
    df['mes'] = df[coluna_data].dt.month
    if tipo_agregacao == 'valor':
        dados_mensais = df.groupby('mes')["VALOR - VENDA (TOTAL) DESC."].sum()
    else:
        dados_mensais = df.groupby('mes').size()
    return {i: dados_mensais.get(i, 0) for i in range(1, 13)}

def calcular_faturamento(ano: int, mes: int) -> (float, dict):
    print("\n--- Verificando Faturamento ---")
    query = f"""
        SELECT "DATA (FATURAMENTO)", "VALOR - VENDA (TOTAL) DESC."
        FROM Vendas 
        WHERE "ATENDIMENTO (ANDAMENTO)" IN ('Finalizado', 'Finalizado Com Faturamento')
        AND strftime('%Y', "DATA (FATURAMENTO)") = '{ano}';
    """
    df = executar_consulta(query)
    df_filtrado_periodo = df[pd.to_datetime(df["DATA (FATURAMENTO)"], errors='coerce').dt.month <= mes]
    total = df_filtrado_periodo["VALOR - VENDA (TOTAL) DESC."].sum()
    print(f"Total Encontrado: {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return total, {}

def calcular_vendas(ano: int, mes: int) -> (float, dict):
    print("\n--- Verificando Vendas ---")
    query = f"""
        SELECT "DATA (RECEBIMENTO PO)", "VALOR - VENDA (TOTAL) DESC."
        FROM Vendas 
        WHERE strftime('%Y', "DATA (RECEBIMENTO PO)") = '{ano}';
    """
    df = executar_consulta(query)
    df_filtrado_periodo = df[pd.to_datetime(df["DATA (RECEBIMENTO PO)"], errors='coerce').dt.month <= mes]
    total = df_filtrado_periodo["VALOR - VENDA (TOTAL) DESC."].sum()
    print(f"Total Encontrado: {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return total, {}

def calcular_pendentes(tipo: str) -> (int, float, dict):
    if tipo == "bm":
        titulo = "BMs Pendentes"
        data_ref_pd, data_vazia_pd = 'DATA (ENVIO DOS RELATÓRIOS)', 'DATA (LIBERAÇÃO BM)'
    else:
        titulo = "Relatórios Pendentes"
        data_ref_pd, data_vazia_pd = 'DATA (FINAL ATENDIMENTO)', 'DATA (ENVIO DOS RELATÓRIOS)'
    
    print(f"\n--- Verificando {titulo} (Total Histórico) ---")
    data_ref_sql, data_vazia_sql = f'"{data_ref_pd}"', f'"{data_vazia_pd}"'
    query = f"""
        SELECT "VALOR - VENDA (TOTAL) DESC.", {data_ref_sql}
        FROM Vendas
        WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
        AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '');
    """
    df = executar_consulta(query)
    qtde_total = len(df)
    valor_total = df["VALOR - VENDA (TOTAL) DESC."].sum()
    print(f"Quantidade Encontrada: {qtde_total}")
    print(f"Valor Total Encontrado: {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return int(qtde_total), valor_total, {}

# --- EXECUÇÃO PRINCIPAL DO DIAGNÓSTICO ---
if __name__ == "__main__":
    print("Iniciando diagnóstico dos cálculos...")
    print("===================================")
    
    # Executa cada cálculo individualmente
    calcular_faturamento(ANO_DE_ANALISE, MES_ATUAL)
    calcular_vendas(ANO_DE_ANALISE, MES_ATUAL)
    calcular_pendentes("bm")
    calcular_pendentes("relatorio")
    
    print("\n===================================")
    print("Diagnóstico concluído.")