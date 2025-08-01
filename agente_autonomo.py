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
NOME_OUTPUT_HTML = "index.html" # Nome final para o GitHub Pages
ANO_DE_ANALISE = 2025
MES_ATUAL = 8 # <<< ALTERAÇÃO APLICADA AQUI
MESES_MAP = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN', 7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}

# --- 2. FERRAMENTAS DE CÁLCULO ---

def executar_consulta(query: str) -> pd.DataFrame:
    """Executa uma consulta e retorna um DataFrame do Pandas."""
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
    """Helper para agrupar dados por mês, retornando um dicionário com 12 meses."""
    if df.empty or coluna_data not in df.columns:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df.dropna(subset=[coluna_data], inplace=True)
    if df.empty:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    df['mes'] = df[coluna_data].dt.month
    if tipo_agregacao == 'valor':
        dados_mensais = df.groupby('mes')["VALOR - VENDA (TOTAL) DESC."].sum()
    else: # contagem
        dados_mensais = df.groupby('mes').size()
    return {MESES_MAP[mes_num]: dados_mensais.get(mes_num, 0) for mes_num in range(1, 13)}

def calcular_faturamento(ano: int, mes_limite: int) -> tuple[float, dict, float]:
    """Calcula faturamento total do período, dados mensais e média."""
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
    """Calcula vendas totais, mensais e a média para um ano específico."""
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
    """Calcula BMs ou Relatórios pendentes para um ano e período específicos."""
    if tipo == "bm":
        data_ref_pd, data_vazia_pd = 'DATA (ENVIO DOS RELATÓRIOS)', 'DATA (LIBERAÇÃO BM)'
    else: # relatorios
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

# --- 3. FASE 2: PREENCHIMENTO DO DASHBOARD ---

def formatar_moeda(valor) -> str:
    """Formata um número para o padrão de moeda brasileiro."""
    if valor is None or not isinstance(valor, (int, float, np.number)): valor = 0.0
    valor_float = float(valor)
    return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        return super(NumpyEncoder, self).default(obj)

def gerar_script_graficos(dados: dict, mes_limite: int) -> str:
    """Gera o bloco <script> completo para os gráficos."""
    fat_mensal_lista = list(dados.get("FATURAMENTO_MENSAL", {}).values())
    ven_mensal_lista = list(dados.get("VENDAS_MENSAL", {}).values())
    bm_mensal_lista = list(dados.get("BM_PENDENTE_MENSAL", {}).values())
    rel_mensal_lista = list(dados.get("RELATORIOS_PENDENTES_MENSAL", {}).values())

    script = f"""
    <script>
        window.addEventListener('load', () => {{
            try {{
                const mesAtual = {mes_limite};
                const todosOsMeses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
                const chartLabels = todosOsMeses.slice(0, mesAtual);

                const formatCurrency = (value) => (value || 0).toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL' }});
                const formatInt = (value) => (value || 0).toLocaleString('pt-BR');
                const formatAxisTick = (value, isCurrency = true) => {{
                    if (value >= 1000000) return (isCurrency ? 'R$ ' : '') + (value / 1000000).toFixed(1) + 'M';
                    if (value >= 1000) return (isCurrency ? 'R$ ' : '') + (value / 1000).toFixed(0) + 'K';
                    return isCurrency ? formatCurrency(value) : formatInt(value);
                }};

                const baseChartOptions = {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, ticks: {{ callback: (val) => formatAxisTick(val, true) }} }}, x: {{ grid: {{ display: false }} }} }}, plugins: {{ legend: {{display: false}}, tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label || ''}}: ${{formatCurrency(c.parsed.y)}}` }} }} }} }};
                const integerChartOptions = {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0, callback: (val) => formatAxisTick(val, false) }} }}, x: {{ grid: {{ display: false }} }} }}, plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label || ''}}: ${{formatInt(c.parsed.y)}}` }} }} }} }};

                new Chart(document.getElementById('faturamentoChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Faturamento', data: {json.dumps(fat_mensal_lista, cls=NumpyEncoder)}.slice(0, mesAtual), backgroundColor: 'rgba(79, 70, 229, 0.6)' }}] }}, options: baseChartOptions }});
                new Chart(document.getElementById('vendasChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Vendas', data: {json.dumps(ven_mensal_lista, cls=NumpyEncoder)}.slice(0, mesAtual), backgroundColor: 'rgba(22, 163, 74, 0.6)' }}] }}, options: baseChartOptions }});
                new Chart(document.getElementById('bmPendenteChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Itens', data: {json.dumps(bm_mensal_lista, cls=NumpyEncoder)}.slice(0, mesAtual), backgroundColor: 'rgba(220, 38, 38, 0.6)' }}] }}, options: integerChartOptions }});
                new Chart(document.getElementById('relatoriosPendentesChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Itens', data: {json.dumps(rel_mensal_lista, cls=NumpyEncoder)}.slice(0, mesAtual), backgroundColor: 'rgba(249, 115, 22, 0.6)' }}] }}, options: integerChartOptions }});
            
            }} catch (error) {{
                console.error("ERRO ao desenhar os gráficos:", error);
            }}
        }});
    </script>
    """
    return script

def gerar_dashboard(ano_atual, mes_atual):
    """Função principal que orquestra o cálculo e a criação do HTML."""
    agora = datetime.now()
    
    print(f"Agente Autonomo Final iniciado.")
    print(f"Ano de Analise: {ano_atual}, Mes de Analise: {mes_atual}")
    print("-" * 30)
    
    # Fase 1: Calcular tudo
    print("Passo 1: Calculando indicadores...")
    fat_total, fat_mensal, fat_media = calcular_faturamento(ano_atual, mes_atual)
    ven_total, ven_mensal, ven_media = calcular_vendas(ano_atual, mes_atual)
    bm_qtde, bm_valor, bm_mensal = calcular_pendentes("bm", ano_atual, mes_atual)
    rel_qtde, rel_valor, rel_mensal = calcular_pendentes("relatorio", ano_atual, mes_atual)
    
    # Fase 2: Atualizar o HTML
    print("\nPasso 2: Atualizando o arquivo do dashboard...")
    try:
        with open(NOME_TEMPLATE_HTML, 'r', encoding='utf-8') as f:
            html_final = f.read()
        
        dados_para_substituir = {
            "FATURAMENTO_TOTAL": formatar_moeda(fat_total),
            "FATURAMENTO_MEDIA": formatar_moeda(fat_media),
            "VENDAS_TOTAL": formatar_moeda(ven_total),
            "VENDAS_MEDIA": formatar_moeda(ven_media),
            "BM_PENDENTE_QTDE_TOTAL": str(bm_qtde),
            "BM_PENDENTE_VALOR_TOTAL": formatar_moeda(bm_valor),
            "RELATORIOS_PENDENTES_QTDE_TOTAL": str(rel_qtde),
            "RELATORIOS_PENDENTES_VALOR_TOTAL": formatar_moeda(rel_valor),
            "DATA_ATUALIZACAO": agora.strftime("%d/%m/%Y %H:%M"),
            "MES_ATUAL": str(mes_atual),
            "MES_ATUAL_NOME": MESES_MAP.get(mes_atual, ''),
            "ANO_DE_ANALISE": str(ano_atual)
        }

        for mes_str, val_mes in fat_mensal.items():
            dados_para_substituir[f"FATURAMENTO_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, val_mes in ven_mensal.items():
            dados_para_substituir[f"VENDAS_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, qtde_mes in bm_mensal.items():
            dados_para_substituir[f"BM_PENDENTE_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"
        for mes_str, qtde_mes in rel_mensal.items():
            dados_para_substituir[f"RELATORIOS_PENDENTES_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"

        for marcador, valor_final in dados_para_substituir.items():
            html_final = html_final.replace(f"{{{{{marcador}}}}}", valor_final)
        
        dados_graficos = {
            "FATURAMENTO_MENSAL": fat_mensal, 
            "VENDAS_MENSAL": ven_mensal, 
            "BM_PENDENTE_MENSAL": bm_mensal,
            "RELATORIOS_PENDENTES_MENSAL": rel_mensal,
            "MES_ATUAL": mes_atual
        }
        script_graficos = gerar_script_graficos(dados_graficos, mes_atual)
        html_final = html_final.replace("{{GRAFICOS_SCRIPT}}", script_graficos)

        with open(NOME_OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_final)
        
        print(f"Dashboard para o ano {ano_atual} atualizado com sucesso!")
    except Exception as e:
        print(f"ERRO ao escrever no dashboard: {e}")

if __name__ == "__main__":
    agora = datetime.now()
    ano_atual = agora.year
    mes_atual = agora.month
    
    gerar_dashboard(ano_atual, mes_atual)
    
    print("-" * 30)
    print("Processo Concluido!")
    print(f"Abra o arquivo '{NOME_OUTPUT_HTML}' para ver o resultado.")
