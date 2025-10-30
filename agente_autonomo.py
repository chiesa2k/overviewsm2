import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, List, Tuple
from datetime import datetime
import json
import numpy as np
import re # Importar a biblioteca re para limpeza mais robusta

# Carrega as variáveis de ambiente
load_dotenv()

# --- 1. CONFIGURAÇÃO ---
NOME_BANCO_DADOS = "gerenciamento.db"
NOME_TEMPLATE_HTML = "dashboard_template.html"
NOME_OUTPUT_HTML = "index.html"
MESES_MAP = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN', 7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}

# --- 2. FERRAMENTAS DE CÁLCULO ---

def limpar_valor_monetario(series: pd.Series) -> pd.Series:
    """Converte uma Series de texto (moeda brasileira) para numérico de forma robusta."""
    if series is None:
         return pd.Series([0.0] * len(series), index=series.index if series is not None else None)
    cleaned_series = series.astype(str)
    def clean_value(value):
        if pd.isna(value): return 0.0
        text = str(value).replace('R$', '').strip()
        if not text: return 0.0
        last_comma = text.rfind(',')
        last_dot = text.rfind('.')
        decimal_separator_pos = max(last_comma, last_dot)
        decimal_separator = ''
        if decimal_separator_pos != -1: decimal_separator = text[decimal_separator_pos]
        if decimal_separator == ',':
            cleaned_text = text.replace('.', '').replace(',', '.')
        elif decimal_separator == '.':
             cleaned_text = text.replace(',', '')
        else:
             cleaned_text = re.sub(r'[^\d]', '', text)
        cleaned_text = re.sub(r'[^\d.]', '', cleaned_text)
        parts = cleaned_text.split('.')
        if len(parts) > 2: cleaned_text = parts[0] + '.' + "".join(parts[1:])
        elif len(parts) == 2 and not parts[0] and parts[1]: cleaned_text = "0." + parts[1]
        try:
            if not cleaned_text or cleaned_text == '.': return 0.0
            return float(cleaned_text)
        except ValueError:
            just_digits = re.sub(r'[^\d]', '', str(value))
            if just_digits:
                 try: return float(just_digits)
                 except ValueError: return 0.0
            return 0.0
    numeric_series = cleaned_series.apply(clean_value)
    return numeric_series

def executar_consulta(query: str) -> pd.DataFrame:
    """Executa uma consulta e retorna um DataFrame do Pandas."""
    print(f"-- Executando SQL: {query[:150]}...") # Aumentado limite para ver mais da query
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    try:
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        print(f"Erro na consulta: {e}")
        return pd.DataFrame()
    finally:
        conexao.close()
    return df

def get_dados_mensais(df: pd.DataFrame, coluna_data: str, tipo_agregacao: str = 'valor', coluna_valor: str = "VALOR - VENDA (TOTAL) DESC.") -> dict:
    """Helper para agrupar dados por mês, retornando um dicionário com 12 meses."""
    if df.empty: # Verificação inicial se o df já está vazio
        # print(f"DEBUG: DataFrame vazio ao entrar em get_dados_mensais para coluna '{coluna_data}'.")
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    if coluna_data not in df.columns:
        print(f"DEBUG: Coluna de data '{coluna_data}' não encontrada no DataFrame para get_dados_mensais.")
        print(f"DEBUG: Colunas disponíveis: {df.columns.tolist()}")
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    # Tentar converter a coluna de data
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    contagem_inicial = len(df)
    df.dropna(subset=[coluna_data], inplace=True) # Remove linhas onde a data é inválida (NaT)
    contagem_final = len(df)
    if contagem_inicial != contagem_final:
        print(f"DEBUG: Removidas {contagem_inicial - contagem_final} linhas com datas inválidas na coluna '{coluna_data}'.")


    if df.empty: # Verifica se o DataFrame ficou vazio após remover NaT
        # print(f"DEBUG: DataFrame vazio após dropna para coluna de data '{coluna_data}'.")
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    # Adiciona try-except para a criação da coluna 'mes'
    try:
        df['mes'] = df[coluna_data].dt.month
    except AttributeError as e:
         print(f"ERRO: Problema ao extrair mês da coluna '{coluna_data}'. Verifique o tipo de dados.")
         print(f"DEBUG: Tipo de dados da coluna '{coluna_data}': {df[coluna_data].dtype}")
         print(f"DEBUG: Exemplo de dados na coluna '{coluna_data}':\n{df[coluna_data].head().to_string()}")
         return {mes_str: 0 for mes_str in MESES_MAP.values()}


    if tipo_agregacao == 'valor':
        if coluna_valor not in df.columns:
            print(f"AVISO: A coluna de valor '{coluna_valor}' não foi encontrada. O cálculo será zerado.")
            return {mes_str: 0 for mes_str in MESES_MAP.values()}
        dados_mensais = df.groupby('mes')[coluna_valor].sum()
    else: # contagem
        dados_mensais = df.groupby('mes').size() # Conta as linhas por mês

    return {MESES_MAP[mes_num]: dados_mensais.get(mes_num, 0) for mes_num in range(1, 13)}

def calcular_faturamento_mensal(ano: int) -> dict:
    """Calcula o faturamento mensal (soma simples) para um ano inteiro, com limpeza de dados."""
    coluna_data_faturamento = "DATA (FATURAMENTO)"
    coluna_valor_faturamento = "VALOR - VENDA (TOTAL) DESC."
    query = f"""
        SELECT 
            "{coluna_data_faturamento}", 
            "{coluna_valor_faturamento}"
        FROM Vendas 
        WHERE strftime('%Y', "{coluna_data_faturamento}") = '{ano}';
    """
    df = executar_consulta(query)
    if coluna_valor_faturamento in df.columns:
        df[coluna_valor_faturamento] = limpar_valor_monetario(df[coluna_valor_faturamento])
    else:
        print(f"ERRO CRÍTICO: A coluna de faturamento '{coluna_valor_faturamento}' não foi encontrada.")
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    return get_dados_mensais(df.copy(), coluna_data_faturamento, tipo_agregacao='valor', coluna_valor=coluna_valor_faturamento)

def calcular_vendas_mensal(ano: int) -> dict:
    """Calcula as vendas mensais para um ano inteiro."""
    coluna_data_vendas = "DATA (RECEBIMENTO PO)"
    coluna_valor_vendas = "VALOR - VENDA (TOTAL) DESC."
    query = f"""
        SELECT "{coluna_data_vendas}", "{coluna_valor_vendas}"
        FROM Vendas 
        WHERE strftime('%Y', "{coluna_data_vendas}") = '{ano}';
    """
    df = executar_consulta(query)
    if coluna_valor_vendas in df.columns:
        df[coluna_valor_vendas] = limpar_valor_monetario(df[coluna_valor_vendas])
    return get_dados_mensais(df.copy(), coluna_data_vendas, coluna_valor=coluna_valor_vendas)

def calcular_pendentes(tipo: str, ano: int) -> tuple[int, float, dict]:
    """Calcula BMs ou Relatórios pendentes para atendimentos iniciados no ano de análise."""

    if tipo == "bm":
        # --- LÓGICA BM PENDENTE - REVERTIDA PARA A ORIGINAL COM AJUSTES ---
        coluna_valor = '"VALOR - VENDA (TOTAL)"'      # Coluna de valor correta (AQ)
        data_ref_sql = '"DATA (ENVIO DOS RELATÓRIOS)"' # Data de referência para mês (preenchida)
        data_vazia_sql = '"DATA (LIBERAÇÃO BM)"'       # Data que deve estar vazia
        data_ano_sql = '"DATA (INÍCIO ATENDIMENTO)"'    # Data para filtrar o ano (AE)

        query = f"""
            SELECT {coluna_valor} AS VALOR_TEMP, {data_ref_sql} AS DATA_REF_TEMP
            FROM Vendas
            WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
            AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '')
            AND strftime('%Y', {data_ano_sql}) = '{ano}';
        """
        coluna_valor_pd = "VALOR_TEMP" # Nome temporário para Pandas
        coluna_data_pd = "DATA_REF_TEMP" # Nome temporário para Pandas

        # --- DEBUG ADICIONADO ---
        print(f"\n--- DEBUG BM PENDENTE (Lógica Data Vazia) ---")
        print(f"Query SQL para BM Pendente:\n{query}")
        # --- FIM DEBUG ---

    elif tipo == "relatorio":
        # Lógica original para Relatórios Pendentes (mantida)
        coluna_valor_total = "VALOR - VENDA (TOTAL) DESC." # Usa DESC aqui
        data_ref_pd_orig, data_vazia_pd = 'DATA (FINAL ATENDIMENTO)', 'DATA (ENVIO DOS RELATÓRIOS)'
        data_ref_sql, data_vazia_sql = f'"{data_ref_pd_orig}"', f'"{data_vazia_pd}"'
        query = f"""
            SELECT "{coluna_valor_total}" AS VALOR_TEMP, {data_ref_sql} AS DATA_REF_TEMP
            FROM Vendas
            WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
            AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '')
            AND strftime('%Y', "DATA (RECEBIMENTO PO)") = '{ano}';
        """
        coluna_valor_pd = "VALOR_TEMP" # Nome temporário
        coluna_data_pd = "DATA_REF_TEMP" # Nome temporário
    else:
        print(f"ERRO: Tipo de pendente desconhecido '{tipo}'")
        return 0, 0.0, {m: 0 for m in MESES_MAP.values()}

    df = executar_consulta(query)

    # --- DEBUG ADICIONADO ---
    if tipo == "bm":
        print(f"\nDataFrame BM Pendente ANTES da limpeza (primeiras 5 linhas):\n{df.head().to_string()}")
    # --- FIM DEBUG ---

    # Aplica a limpeza robusta na coluna de valor (usando o nome temporário)
    if coluna_valor_pd in df.columns:
        df[coluna_valor_pd] = limpar_valor_monetario(df[coluna_valor_pd])
    else:
         print(f"AVISO: Coluna de valor '{coluna_valor_pd}' não encontrada para pendentes do tipo '{tipo}'.")
         df[coluna_valor_pd] = 0.0

    # --- DEBUG ADICIONADO ---
    if tipo == "bm":
         print(f"\nDataFrame BM Pendente DEPOIS da limpeza (primeiras 5 linhas):\n{df.head().to_string()}")
         print(f"Total de linhas encontradas para BM Pendente: {len(df)}")
         print(f"Soma do valor total para BM Pendente: {df[coluna_valor_pd].sum()}")
         print(f"--- FIM DEBUG BM PENDENTE ---\n")
    # --- FIM DEBUG ---

    qtde_total = len(df)
    valor_total = df[coluna_valor_pd].sum()
    
    # Passa o nome correto da coluna de data (renomeada) e valor (renomeada) para get_dados_mensais
    qtde_mensal = get_dados_mensais(df.copy(), coluna_data_pd, 'contagem', coluna_valor=coluna_valor_pd)
    
    return int(qtde_total), valor_total, qtde_mensal

# --- 3. FASE 2: PREENCHIMENTO DO DASHBOARD ---
# O restante do código permanece o mesmo...

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

def gerar_script_graficos(dados: dict, mes_limite_grafico: int) -> str:
    """Gera o bloco <script> completo para os gráficos."""
    fat_mensal_lista = list(dados.get("FATURAMENTO_MENSAL", {}).values())
    fat_mensal_2024_lista = list(dados.get("FATURAMENTO_MENSAL_2024", {}).values())
    ven_mensal_lista = list(dados.get("VENDAS_MENSAL", {}).values())
    ven_mensal_2024_lista = list(dados.get("VENDAS_MENSAL_2024", {}).values())
    bm_mensal_lista = list(dados.get("BM_PENDENTE_MENSAL", {}).values())
    rel_mensal_lista = list(dados.get("RELATORIOS_PENDENTES_MENSAL", {}).values())

    script = f"""
    <script>
        window.addEventListener('load', () => {{
            try {{
                const mesLimiteGrafico = {mes_limite_grafico};
                const todosOsMeses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
                const chartLabels = todosOsMeses.slice(0, mesLimiteGrafico);

                const formatCurrency = (value) => (value || 0).toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL' }});
                const formatInt = (value) => (value || 0).toLocaleString('pt-BR');
                const formatAxisTick = (value, isCurrency = true) => {{
                    if (value >= 1000000) return (isCurrency ? 'R$ ' : '') + (value / 1000000).toFixed(1) + 'M';
                    if (value >= 1000) return (isCurrency ? 'R$ ' : '') + (value / 1000).toFixed(0) + 'K';
                    return isCurrency ? formatCurrency(value) : formatInt(value);
                }};

                const baseChartOptions = {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, ticks: {{ callback: (val) => formatAxisTick(val, true) }} }}, x: {{ grid: {{ display: false }} }} }}, plugins: {{ legend: {{display: true}}, tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label || ''}}: ${{formatCurrency(c.parsed.y)}}` }} }} }} }};
                const integerChartOptions = {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0, callback: (val) => formatAxisTick(val, false) }} }}, x: {{ grid: {{ display: false }} }} }}, plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label || ''}}: ${{formatInt(c.parsed.y)}}` }} }} }} }};

                new Chart(document.getElementById('faturamentoChart'), {{
                    type: 'bar',
                    data: {{
                        labels: chartLabels,
                        datasets: [
                            {{
                                label: 'Faturamento 2025',
                                type: 'bar',
                                data: {json.dumps(fat_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                backgroundColor: 'rgba(79, 70, 229, 0.6)'
                            }},
                            {{
                                label: 'Faturamento 2024',
                                type: 'line',
                                data: {json.dumps(fat_mensal_2024_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                borderColor: 'rgba(220, 38, 38, 0.8)',
                                backgroundColor: 'rgba(220, 38, 38, 0.1)',
                                tension: 0.1,
                                fill: false
                            }}
                        ]
                    }},
                    options: baseChartOptions
                }});

                new Chart(document.getElementById('vendasChart'), {{
                    type: 'bar',
                    data: {{
                        labels: chartLabels,
                        datasets: [
                             {{
                                label: 'Vendas 2025',
                                type: 'bar',
                                data: {json.dumps(ven_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                backgroundColor: 'rgba(22, 163, 74, 0.6)'
                            }},
                            {{
                                label: 'Vendas 2024',
                                type: 'line',
                                data: {json.dumps(ven_mensal_2024_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                borderColor: 'rgba(220, 38, 38, 0.8)',
                                backgroundColor: 'rgba(220, 38, 38, 0.1)',
                                tension: 0.1,
                                fill: false
                            }}
                        ]
                    }},
                    options: baseChartOptions
                }});

                new Chart(document.getElementById('bmPendenteChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Itens', data: {json.dumps(bm_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico), backgroundColor: 'rgba(220, 38, 38, 0.6)' }}] }}, options: integerChartOptions }});
                new Chart(document.getElementById('relatoriosPendentesChart'), {{ type: 'bar', data: {{ labels: chartLabels, datasets: [{{ label: 'Itens', data: {json.dumps(rel_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico), backgroundColor: 'rgba(249, 115, 22, 0.6)' }}] }}, options: integerChartOptions }});
            
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
    
    mes_limite_analise = mes_atual - 1
    ano_anterior = ano_atual - 1
    
    print(f"Agente Autonomo Final iniciado.")
    print(f"Ano de Analise: {ano_atual}, Mes de Exibicao: {mes_atual}, Mes de Analise Consolidada: {mes_limite_analise}")
    print("-" * 30)
    
    print("Passo 1: Calculando indicadores...")
    fat_mensal = calcular_faturamento_mensal(ano_atual)
    ven_mensal = calcular_vendas_mensal(ano_atual)
    fat_mensal_2024 = calcular_faturamento_mensal(ano_anterior)
    ven_mensal_2024 = calcular_vendas_mensal(ano_anterior)

    fat_total_exibicao = sum(list(fat_mensal.values())[:mes_atual])
    ven_total_exibicao = sum(list(ven_mensal.values())[:mes_atual])
    fat_total_analise = sum(list(fat_mensal.values())[:mes_limite_analise])
    ven_total_analise = sum(list(ven_mensal.values())[:mes_limite_analise])
    fat_total_2024_comp = sum(list(fat_mensal_2024.values())[:mes_limite_analise])
    ven_total_2024_comp = sum(list(ven_mensal_2024.values())[:mes_limite_analise])
    fat_media_correta = fat_total_analise / mes_limite_analise if mes_limite_analise > 0 else 0
    ven_media_correta = ven_total_analise / mes_limite_analise if mes_limite_analise > 0 else 0
    bm_qtde, bm_valor, bm_mensal = calcular_pendentes("bm", ano_atual)
    rel_qtde, rel_valor, rel_mensal = calcular_pendentes("relatorio", ano_atual)
    variacao_faturamento = ((fat_total_analise - fat_total_2024_comp) / fat_total_2024_comp * 100) if fat_total_2024_comp > 0 else 0
    variacao_faturamento_classe = "var-positive" if variacao_faturamento >= 0 else "var-negative"
    variacao_vendas = ((ven_total_analise - ven_total_2024_comp) / ven_total_2024_comp * 100) if ven_total_2024_comp > 0 else 0
    variacao_vendas_classe = "var-positive" if variacao_vendas >= 0 else "var-negative"
    
    print("\nPasso 2: Atualizando o arquivo do dashboard...")
    try:
        with open(NOME_TEMPLATE_HTML, 'r', encoding='utf-8') as f:
            html_final = f.read()
        
        dados_para_substituir = {
            "FATURAMENTO_TOTAL": formatar_moeda(fat_total_exibicao),
            "VENDAS_TOTAL": formatar_moeda(ven_total_exibicao),
            "FATURAMENTO_MEDIA": formatar_moeda(fat_media_correta),
            "FATURAMENTO_TOTAL_2024": formatar_moeda(fat_total_2024_comp),
            "FATURAMENTO_VARIACAO": f"{variacao_faturamento:+.2f}%".replace('.',','),
            "FATURAMENTO_VARIACAO_CLASSE": variacao_faturamento_classe,
            "VENDAS_MEDIA": formatar_moeda(ven_media_correta),
            "VENDAS_TOTAL_2024": formatar_moeda(ven_total_2024_comp),
            "VENDAS_VARIACAO": f"{variacao_vendas:+.2f}%".replace('.',','),
            "VENDAS_VARIACAO_CLASSE": variacao_vendas_classe,
            "BM_PENDENTE_QTDE_TOTAL": str(bm_qtde),
            "BM_PENDENTE_VALOR_TOTAL": formatar_moeda(bm_valor),
            "RELATORIOS_PENDENTES_QTDE_TOTAL": str(rel_qtde),
            "RELATORIOS_PENDENTES_VALOR_TOTAL": formatar_moeda(rel_valor),
            "DATA_ATUALIZACAO": agora.strftime("%d/%m/%Y %H:%M"),
            "MES_ATUAL": str(mes_atual),
            "MES_ATUAL_NOME": MESES_MAP.get(mes_atual, ''),
            "ANO_DE_ANALISE": str(ano_atual),
        }

        for mes_str, val_mes in fat_mensal.items(): dados_para_substituir[f"FATURAMENTO_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, val_mes in ven_mensal.items(): dados_para_substituir[f"VENDAS_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, qtde_mes in bm_mensal.items(): dados_para_substituir[f"BM_PENDENTE_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"
        for mes_str, qtde_mes in rel_mensal.items(): dados_para_substituir[f"RELATORIOS_PENDENTES_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"

        for marcador, valor_final in dados_para_substituir.items():
            html_final = html_final.replace(f"{{{{{marcador}}}}}", valor_final)
        
        dados_graficos = {
            "FATURAMENTO_MENSAL": fat_mensal, 
            "FATURAMENTO_MENSAL_2024": fat_mensal_2024,
            "VENDAS_MENSAL": ven_mensal, 
            "VENDAS_MENSAL_2024": ven_mensal_2024,
            "BM_PENDENTE_MENSAL": bm_mensal,
            "RELATORIOS_PENDENTES_MENSAL": rel_mensal,
        }
        
        script_graficos = gerar_script_graficos(dados_graficos, mes_limite_analise)
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
