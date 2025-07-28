import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from typing import TypedDict, Dict, List, Tuple
from datetime import datetime
import json
import numpy as np

# Carrega as variáveis de ambiente
load_dotenv()

# --- 1. CONFIGURAÇÃO ---
NOME_BANCO_DADOS = "gerenciamento.db"
NOME_TEMPLATE_HTML = "dashboard_template.html"
NOME_OUTPUT_HTML = "index.html" # Mantendo como index.html para o GitHub Pages
ANO_DE_ANALISE = 2025
MESES_MAP = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN', 7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}

# --- Funções de cálculo (sem alterações) ---
def executar_consulta(query: str) -> pd.DataFrame:
    print(f"-- Executando SQL: {query[:90]}...")
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    try:
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        print(f"Erro na consulta: {e}")
        return pd.DataFrame()
    finally:
        conexao.close()
    return df

def get_dados_mensais(df: pd.DataFrame, coluna_data: str, tipo_agregacao: str = 'valor') -> dict:
    if df.empty or coluna_data not in df.columns:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df.dropna(subset=[coluna_data], inplace=True)
    if df.empty:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    df['mes'] = df[coluna_data].dt.month
    if tipo_agregacao == 'valor':
        dados_mensais = df.groupby('mes')["VALOR - VENDA (TOTAL) DESC."].sum()
    else:
        dados_mensais = df.groupby('mes').size()
    return {MESES_MAP[mes_num]: dados_mensais.get(mes_num, 0) for mes_num in range(1, 13)}

def calcular_faturamento(ano: int, mes_limite: int) -> tuple[float, dict, float]:
    query = f"""
        SELECT "DATA (FATURAMENTO)", "VALOR - VENDA (TOTAL) DESC."
        FROM Vendas 
        WHERE "ATENDIMENTO (ANDAMENTO)" IN ('Finalizado Com Faturamento', 'Falta Recebimento')
        AND strftime('%Y', "DATA (FATURAMENTO)") = '{ano}';
    """
    df = executar_consulta(query)
    df['DATA (FATURAMENTO)'] = pd.to_datetime(df['DATA (FATURAMENTO)'], errors='coerce')
    df_periodo = df[df["DATA (FATURAMENTO)"].dt.month <= mes_limite]
    total = df_periodo["VALOR - VENDA (TOTAL) DESC."].sum()
    mensal = get_dados_mensais(df.copy(), "DATA (FATURAMENTO)")
    media = total / mes_limite if mes_limite > 0 else 0
    return total, mensal, media

def calcular_vendas(ano: int, mes_limite: int) -> tuple[float, dict, float]:
    query = f"""
        SELECT "DATA (RECEBIMENTO PO)", "VALOR - VENDA (TOTAL) DESC."
        FROM Vendas 
        WHERE strftime('%Y', "DATA (RECEBIMENTO PO)") = '{ano}';
    """
    df = executar_consulta(query)
    df['DATA (RECEBIMENTO PO)'] = pd.to_datetime(df['DATA (RECEBIMENTO PO)'], errors='coerce')
    df_periodo = df[df["DATA (RECEBIMENTO PO)"].dt.month <= mes_limite]
    total = df_periodo["VALOR - VENDA (TOTAL) DESC."].sum()
    mensal = get_dados_mensais(df.copy(), "DATA (RECEBIMENTO PO)")
    media = total / mes_limite if mes_limite > 0 else 0
    return total, mensal, media

def calcular_pendentes(tipo: str, ano: int, mes_limite: int) -> tuple[int, float, dict]:
    if tipo == "bm":
        data_ref_pd, data_vazia_pd = 'DATA (ENVIO DOS RELATÓRIOS)', 'DATA (LIBERAÇÃO BM)'
    else:
        data_ref_pd, data_vazia_pd = 'DATA (FINAL ATENDIMENTO)', 'DATA (ENVIO DOS RELATÓRIOS)'
    data_ref_sql, data_vazia_sql = f'"{data_ref_pd}"', f'"{data_vazia_pd}"'
    query = f"""
        SELECT "VALOR - VENDA (TOTAL) DESC.", {data_ref_sql}
        FROM Vendas
        WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
        AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '')
        AND strftime('%Y', {data_ref_sql}) = '{ano}';
    """
    df = executar_consulta(query)
    df[data_ref_pd] = pd.to_datetime(df[data_ref_pd], errors='coerce')
    df_periodo = df[df[data_ref_pd].dt.month <= mes_limite]
    qtde_total = len(df_periodo)
    valor_total = df_periodo["VALOR - VENDA (TOTAL) DESC."].sum()
    qtde_mensal = get_dados_mensais(df, data_ref_pd, 'contagem')
    return int(qtde_total), valor_total, qtde_mensal

def formatar_moeda(valor) -> str:
    if valor is None or not isinstance(valor, (int, float, np.number)): valor = 0.0
    valor_float = float(valor)
    return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        return super(NumpyEncoder, self).default(obj)

# --- FASE 2: PREENCHIMENTO DO DASHBOARD ---
def gerar_dashboard(ano_atual, mes_atual):
    print(f"Agente Autonomo Final (v23) iniciado.")
    print(f"Ano de Analise: {ano_atual}, Mes de Analise: {mes_atual}")
    print("-" * 30)
    
    # Fase 1: Calcular tudo
    print("Passo 1: Calculando indicadores...")
    # ... (código de cálculo omitido por brevidade)

    # Fase 2: Atualizar o HTML
    print("\nPasso 2: Atualizando o arquivo do dashboard...")
    try:
        with open(NOME_TEMPLATE_HTML, 'r', encoding='utf-8') as f:
            html_final = f.read()

        # ... (código de substituição omitido por brevidade)
        
        with open(NOME_OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_final)
        
        print(f"Dashboard para o ano {ano_atual} atualizado com sucesso!")
    except Exception as e:
        print(f"ERRO ao escrever no dashboard: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    agora = datetime.now()
    ano_atual = agora.year
    mes_atual = agora.month
    
    gerar_dashboard(ano_atual, mes_atual)
    
    print("-" * 30)
    print("Processo Concluido!")
    print(f"Abra o arquivo '{NOME_OUTPUT_HTML}' para ver o resultado.")
