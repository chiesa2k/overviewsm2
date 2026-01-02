import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, List, Tuple
from datetime import datetime
import json
import numpy as np
import re

# Carrega as variáveis de ambiente
load_dotenv()

# --- 1. CONFIGURAÇÃO ---
NOME_BANCO_DADOS = "gerenciamento.db"
NOME_TEMPLATE_HTML = "dashboard_template.html"
# O nome de saída será dinâmico agora
MESES_MAP = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN', 7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}

# --- 2. FERRAMENTAS DE CÁLCULO (MANTIDAS IGUAIS) ---

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
    print(f"-- Executando SQL: {query[:100]}...") 
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
    if df.empty:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    if coluna_data not in df.columns:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df.dropna(subset=[coluna_data], inplace=True)

    if df.empty:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}

    try:
        df['mes'] = df[coluna_data].dt.month
    except AttributeError:
         return {mes_str: 0 for mes_str in MESES_MAP.values()}

    if tipo_agregacao == 'valor':
        if coluna_valor not in df.columns:
            return {mes_str: 0 for mes_str in MESES_MAP.values()}
        dados_mensais = df.groupby('mes')[coluna_valor].sum()
    else: 
        dados_mensais = df.groupby('mes').size()

    return {MESES_MAP[mes_num]: dados_mensais.get(mes_num, 0) for mes_num in range(1, 13)}

def calcular_faturamento_mensal(ano: int) -> dict:
    coluna_data_faturamento = "DATA (FATURAMENTO)"
    coluna_valor_faturamento = "VALOR - VENDA (TOTAL) DESC."
    query = f"""
        SELECT "{coluna_data_faturamento}", "{coluna_valor_faturamento}"
        FROM Vendas WHERE strftime('%Y', "{coluna_data_faturamento}") = '{ano}';
    """
    df = executar_consulta(query)
    if coluna_valor_faturamento in df.columns:
        df[coluna_valor_faturamento] = limpar_valor_monetario(df[coluna_valor_faturamento])
    else:
        return {mes_str: 0 for mes_str in MESES_MAP.values()}
    return get_dados_mensais(df.copy(), coluna_data_faturamento, tipo_agregacao='valor', coluna_valor=coluna_valor_faturamento)

def calcular_vendas_mensal(ano: int) -> dict:
    coluna_data_vendas = "DATA (RECEBIMENTO PO)"
    coluna_valor_vendas = "VALOR - VENDA (TOTAL) DESC."
    query = f"""
        SELECT "{coluna_data_vendas}", "{coluna_valor_vendas}"
        FROM Vendas WHERE strftime('%Y', "{coluna_data_vendas}") = '{ano}';
    """
    df = executar_consulta(query)
    if coluna_valor_vendas in df.columns:
        df[coluna_valor_vendas] = limpar_valor_monetario(df[coluna_valor_vendas])
    return get_dados_mensais(df.copy(), coluna_data_vendas, coluna_valor=coluna_valor_vendas)

def calcular_pendentes(tipo: str, ano: int) -> tuple[int, float, dict]:
    if tipo == "bm":
        coluna_valor = '"VALOR - VENDA (TOTAL)"'
        data_ref_sql = '"DATA (ENVIO DOS RELATÓRIOS)"'
        data_vazia_sql = '"DATA (LIBERAÇÃO BM)"'
        data_ano_sql = '"DATA (INÍCIO ATENDIMENTO)"'

        query = f"""
            SELECT {coluna_valor} AS VALOR_TEMP, {data_ref_sql} AS DATA_REF_TEMP
            FROM Vendas
            WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
            AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '')
            AND strftime('%Y', {data_ano_sql}) = '{ano}';
        """
        coluna_valor_pd = "VALOR_TEMP"
        coluna_data_pd = "DATA_REF_TEMP"

    elif tipo == "relatorio":
        coluna_valor_total = "VALOR - VENDA (TOTAL) DESC."
        data_ref_pd_orig, data_vazia_pd = 'DATA (FINAL ATENDIMENTO)', 'DATA (ENVIO DOS RELATÓRIOS)'
        data_ref_sql, data_vazia_sql = f'"{data_ref_pd_orig}"', f'"{data_vazia_pd}"'
        query = f"""
            SELECT "{coluna_valor_total}" AS VALOR_TEMP, {data_ref_sql} AS DATA_REF_TEMP
            FROM Vendas
            WHERE ({data_ref_sql} IS NOT NULL AND {data_ref_sql} != '')
            AND ({data_vazia_sql} IS NULL OR {data_vazia_sql} = '')
            AND strftime('%Y', "DATA (RECEBIMENTO PO)") = '{ano}';
        """
        coluna_valor_pd = "VALOR_TEMP"
        coluna_data_pd = "DATA_REF_TEMP"
    else:
        return 0, 0.0, {m: 0 for m in MESES_MAP.values()}

    df = executar_consulta(query)

    if coluna_valor_pd in df.columns:
        df[coluna_valor_pd] = limpar_valor_monetario(df[coluna_valor_pd])
    else:
         df[coluna_valor_pd] = 0.0

    qtde_total = len(df)
    valor_total = df[coluna_valor_pd].sum()
    qtde_mensal = get_dados_mensais(df.copy(), coluna_data_pd, 'contagem', coluna_valor=coluna_valor_pd)
    
    return int(qtde_total), valor_total, qtde_mensal

# --- 3. FASE 2: GERAÇÃO DO DASHBOARD E BOTÃO MÁGICO ---

def formatar_moeda(valor) -> str:
    if valor is None or not isinstance(valor, (int, float, np.number)): valor = 0.0
    valor_float = float(valor)
    return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        return super(NumpyEncoder, self).default(obj)

def gerar_script_graficos(dados: dict, mes_limite_grafico: int) -> str:
    """Gera o script dos gráficos com base nos dados fornecidos."""
    fat_mensal_lista = list(dados.get("FATURAMENTO_MENSAL", {}).values())
    fat_mensal_ant_lista = list(dados.get("FATURAMENTO_MENSAL_ANT", {}).values()) # Genérico ANT (Anterior)
    ven_mensal_lista = list(dados.get("VENDAS_MENSAL", {}).values())
    ven_mensal_ant_lista = list(dados.get("VENDAS_MENSAL_ANT", {}).values()) # Genérico ANT
    bm_mensal_lista = list(dados.get("BM_PENDENTE_MENSAL", {}).values())
    rel_mensal_lista = list(dados.get("RELATORIOS_PENDENTES_MENSAL", {}).values())
    
    # Rótulos dinâmicos para a legenda
    ano_atual_label = str(dados.get("ANO_ATUAL_LABEL", "Atual"))
    ano_ant_label = str(dados.get("ANO_ANTERIOR_LABEL", "Anterior"))

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
                                label: 'Faturamento {ano_atual_label}',
                                type: 'bar',
                                data: {json.dumps(fat_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                backgroundColor: 'rgba(79, 70, 229, 0.6)'
                            }},
                            {{
                                label: 'Faturamento {ano_ant_label}',
                                type: 'line',
                                data: {json.dumps(fat_mensal_ant_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
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
                                label: 'Vendas {ano_atual_label}',
                                type: 'bar',
                                data: {json.dumps(ven_mensal_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
                                backgroundColor: 'rgba(22, 163, 74, 0.6)'
                            }},
                            {{
                                label: 'Vendas {ano_ant_label}',
                                type: 'line',
                                data: {json.dumps(ven_mensal_ant_lista, cls=NumpyEncoder)}.slice(0, mesLimiteGrafico),
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

def injetar_botao_navegacao(html_content: str, texto_botao: str, link_destino: str) -> str:
    """Insere um botão flutuante elegante no canto da tela via HTML/CSS."""
    botao_html = f"""
    <style>
        .floating-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #4F46E5;
            color: white;
            padding: 10px 20px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            z-index: 9999;
            font-family: sans-serif;
            border: 2px solid white;
        }}
        .floating-btn:hover {{
            background-color: #4338ca;
            transform: scale(1.05);
            box-shadow: 0 6px 8px rgba(0,0,0,0.2);
        }}
    </style>
    <a href="{link_destino}" class="floating-btn">📅 {texto_botao}</a>
    """
    # Injeta antes do fechamento do body
    return html_content.replace("</body>", f"{botao_html}\n</body>")

def gerar_dashboard(ano_analise, mes_exibicao, nome_arquivo_saida, botao_texto, botao_link):
    """Função genérica para gerar um dashboard de qualquer ano."""
    
    # Define o limite de análise (meses anteriores ao atual)
    # Se for um ano passado (ex: 2025 quando estamos em 2026), queremos ver todos os 12 meses.
    ano_real_sistema = datetime.now().year
    
    if ano_analise < ano_real_sistema:
        mes_limite_analise = 12 # Ano fechado, mostra tudo
        mes_exibicao = 12       # Gráficos vão até DEZ
    else:
        mes_limite_analise = mes_exibicao - 1 # Ano corrente, mostra até mês passado
        if mes_limite_analise < 1: mes_limite_analise = 1 # Proteção para Janeiro

    ano_anterior = ano_analise - 1
    
    print(f"Gerando Dashboard: {nome_arquivo_saida}")
    print(f"Ano Foco: {ano_analise} | Comparativo: {ano_anterior} | Meses Exibidos: {mes_exibicao}")

    # Cálculos
    fat_mensal = calcular_faturamento_mensal(ano_analise)
    ven_mensal = calcular_vendas_mensal(ano_analise)
    fat_mensal_ant = calcular_faturamento_mensal(ano_anterior)
    ven_mensal_ant = calcular_vendas_mensal(ano_anterior)

    # Totais
    fat_total_exibicao = sum(list(fat_mensal.values())[:mes_exibicao])
    ven_total_exibicao = sum(list(ven_mensal.values())[:mes_exibicao])
    
    # Totais para Variação (Considera meses fechados)
    fat_total_analise = sum(list(fat_mensal.values())[:mes_limite_analise])
    fat_total_ant_comp = sum(list(fat_mensal_ant.values())[:mes_limite_analise])
    
    ven_total_analise = sum(list(ven_mensal.values())[:mes_limite_analise])
    ven_total_ant_comp = sum(list(ven_mensal_ant.values())[:mes_limite_analise])

    # Médias
    fat_media_correta = fat_total_analise / mes_limite_analise if mes_limite_analise > 0 else 0
    ven_media_correta = ven_total_analise / mes_limite_analise if mes_limite_analise > 0 else 0

    # Pendentes
    bm_qtde, bm_valor, bm_mensal = calcular_pendentes("bm", ano_analise)
    rel_qtde, rel_valor, rel_mensal = calcular_pendentes("relatorio", ano_analise)

    # Variações
    variacao_faturamento = ((fat_total_analise - fat_total_ant_comp) / fat_total_ant_comp * 100) if fat_total_ant_comp > 0 else 0
    variacao_faturamento_classe = "var-positive" if variacao_faturamento >= 0 else "var-negative"
    
    variacao_vendas = ((ven_total_analise - ven_total_ant_comp) / ven_total_ant_comp * 100) if ven_total_ant_comp > 0 else 0
    variacao_vendas_classe = "var-positive" if variacao_vendas >= 0 else "var-negative"
    
    try:
        with open(NOME_TEMPLATE_HTML, 'r', encoding='utf-8') as f:
            html_final = f.read()
        
        # Mapa de Substituição
        dados_para_substituir = {
            "FATURAMENTO_TOTAL": formatar_moeda(fat_total_exibicao),
            "VENDAS_TOTAL": formatar_moeda(ven_total_exibicao),
            "FATURAMENTO_MEDIA": formatar_moeda(fat_media_correta),
            "FATURAMENTO_TOTAL_2024": formatar_moeda(fat_total_ant_comp), # Mantivemos a chave ID do template
            "FATURAMENTO_VARIACAO": f"{variacao_faturamento:+.2f}%".replace('.',','),
            "FATURAMENTO_VARIACAO_CLASSE": variacao_faturamento_classe,
            "VENDAS_MEDIA": formatar_moeda(ven_media_correta),
            "VENDAS_TOTAL_2024": formatar_moeda(ven_total_ant_comp), # Mantivemos a chave ID do template
            "VENDAS_VARIACAO": f"{variacao_vendas:+.2f}%".replace('.',','),
            "VENDAS_VARIACAO_CLASSE": variacao_vendas_classe,
            "BM_PENDENTE_QTDE_TOTAL": str(bm_qtde),
            "BM_PENDENTE_VALOR_TOTAL": formatar_moeda(bm_valor),
            "RELATORIOS_PENDENTES_QTDE_TOTAL": str(rel_qtde),
            "RELATORIOS_PENDENTES_VALOR_TOTAL": formatar_moeda(rel_valor),
            "DATA_ATUALIZACAO": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "MES_ATUAL": str(mes_exibicao),
            "MES_ATUAL_NOME": MESES_MAP.get(mes_exibicao, ''),
            "ANO_DE_ANALISE": str(ano_analise),
        }

        # Substituição de listas mensais no HTML (tabelas se houver)
        for mes_str, val_mes in fat_mensal.items(): dados_para_substituir[f"FATURAMENTO_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, val_mes in ven_mensal.items(): dados_para_substituir[f"VENDAS_MENSAL_{mes_str}"] = formatar_moeda(val_mes)
        for mes_str, qtde_mes in bm_mensal.items(): dados_para_substituir[f"BM_PENDENTE_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"
        for mes_str, qtde_mes in rel_mensal.items(): dados_para_substituir[f"RELATORIOS_PENDENTES_MENSAL_{mes_str}"] = f"{int(qtde_mes)} itens"

        for marcador, valor_final in dados_para_substituir.items():
            html_final = html_final.replace(f"{{{{{marcador}}}}}", valor_final)
        
        # Preparar dados para Gráficos
        dados_graficos = {
            "FATURAMENTO_MENSAL": fat_mensal, 
            "FATURAMENTO_MENSAL_ANT": fat_mensal_ant,
            "VENDAS_MENSAL": ven_mensal, 
            "VENDAS_MENSAL_ANT": ven_mensal_ant,
            "BM_PENDENTE_MENSAL": bm_mensal,
            "RELATORIOS_PENDENTES_MENSAL": rel_mensal,
            "ANO_ATUAL_LABEL": ano_analise,
            "ANO_ANTERIOR_LABEL": ano_anterior
        }
        
        script_graficos = gerar_script_graficos(dados_graficos, mes_exibicao)
        html_final = html_final.replace("{{GRAFICOS_SCRIPT}}", script_graficos) 

        # --- AQUI ESTÁ A MÁGICA: INJETA O BOTÃO ---
        html_final = injetar_botao_navegacao(html_final, botao_texto, botao_link)

        with open(nome_arquivo_saida, "w", encoding="utf-8") as f:
            f.write(html_final)
        
        print(f"Sucesso: {nome_arquivo_saida}")
        return True
    except Exception as e:
        print(f"ERRO ao escrever no dashboard {nome_arquivo_saida}: {e}")
        return False

if __name__ == "__main__":
    agora = datetime.now()
    ano_atual_sistema = agora.year
    mes_atual_sistema = agora.month
    
    print("="*40)
    print(f"INICIANDO GERAÇÃO MULTI-ANO - DATA: {agora}")
    
    # 1. Gera o Dashboard HISTÓRICO (2025)
    # Ele será salvo como 'historico_2025.html'
    # O botão dele apontará para 'index.html' (Voltar para 2026)
    gerar_dashboard(
        ano_analise=2025, 
        mes_exibicao=12, # Mostra o ano completo
        nome_arquivo_saida="historico_2025.html",
        botao_texto=f"Ver Atual ({ano_atual_sistema})",
        botao_link="index.html"
    )
    
    print("-" * 20)

    # 2. Gera o Dashboard ATUAL (2026)
    # Ele será salvo como 'index.html' (O padrão que o GitHub Pages abre)
    # O botão dele apontará para 'historico_2025.html' (Ver Passado)
    gerar_dashboard(
        ano_analise=ano_atual_sistema, 
        mes_exibicao=mes_atual_sistema,
        nome_arquivo_saida="index.html",
        botao_texto="Ver Histórico 2025",
        botao_link="historico_2025.html"
    )
    
    print("="*40)
    print("PROCESSO CONCLUÍDO COM SUCESSO!")