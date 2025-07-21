import sqlite3
import pandas as pd

NOME_BANCO_DADOS = "gerenciamento.db"

def executar_consulta(query: str) -> pd.DataFrame:
    """Executa uma consulta e retorna um DataFrame do Pandas."""
    print(f"-- Executando SQL: {query[:80]}...")
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    try:
        df = pd.read_sql_query(query, conexao)
    finally:
        conexao.close()
    return df

def diagnosticar_bms_pendentes():
    """Diagnostica a contagem de BMs Pendentes SEM filtro de ano."""
    print("\n--- DIAGNOSTICANDO BMs PENDENTES (TOTAL) ---")
    query = """
        SELECT COUNT(*), SUM("VALOR - VENDA (TOTAL) DESC.")
        FROM Vendas
        WHERE ("DATA (ENVIO DOS RELATÓRIOS)" IS NOT NULL AND "DATA (ENVIO DOS RELATÓRIOS)" != '')
        AND ("DATA (LIBERAÇÃO BM)" IS NULL OR "DATA (LIBERAÇÃO BM)" = '');
    """
    df = executar_consulta(query)
    qtde = df.iloc[0, 0] or 0
    valor = df.iloc[0, 1] or 0.0
    print(f"Resultado: {int(qtde)} BMs pendentes, somando um valor de R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return int(qtde)

def diagnosticar_relatorios_pendentes():
    """Diagnostica a contagem de Relatórios Pendentes SEM filtro de ano."""
    print("\n--- DIAGNOSTICANDO RELATÓRIOS PENDENTES (TOTAL) ---")
    query = """
        SELECT COUNT(*), SUM("VALOR - VENDA (TOTAL) DESC.")
        FROM Vendas
        WHERE ("DATA (FINAL ATENDIMENTO)" IS NOT NULL AND "DATA (FINAL ATENDIMENTO)" != '')
        AND ("DATA (ENVIO DOS RELATÓRIOS)" IS NULL OR "DATA (ENVIO DOS RELATÓRIOS)" = '');
    """
    df = executar_consulta(query)
    qtde = df.iloc[0, 0] or 0
    valor = df.iloc[0, 1] or 0.0
    print(f"Resultado: {int(qtde)} relatórios pendentes, somando um valor de R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return int(qtde)

if __name__ == "__main__":
    print("Iniciando diagnóstico de pendências...")
    diagnosticar_bms_pendentes()
    diagnosticar_relatorios_pendentes()
    print("\nDiagnóstico concluído.")