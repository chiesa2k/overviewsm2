import os
from datetime import datetime

# Tenta importar as funções dos seus outros dois scripts.
# É importante que os arquivos 'migracao_excel_db.py' e 'agente_autonomo.py'
# estejam na mesma pasta que este script.
try:
    from migracao_excel_db import migrar_dados
    from agente_autonomo import gerar_dashboard
except ImportError as e:
    print(f"ERRO: Não foi possível encontrar os scripts necessários.")
    print(f"Certifique-se de que 'migracao_excel_db.py' e 'agente_autonomo.py' estão na mesma pasta.")
    print(f"Detalhe do erro: {e}")
    exit() # Encerra o script se não encontrar os arquivos.

# --- CONFIGURAÇÃO PARA A MENSAGEM FINAL ---
# O nome do arquivo final gerado pelo agente_autonomo.py
NOME_OUTPUT_HTML = "dashboard.html" 

def executar_processo_completo():
    """
    Orquestra a execução completa do processo de BI:
    1. Migra os dados do Excel para o banco de dados.
    2. Gera o dashboard HTML com os dados atualizados.
    """
    print("🚀 INICIANDO PROCESSO DE ATUALIZAÇÃO COMPLETA DO DASHBOARD 🚀")
    print("="*60)
    
    # --- ETAPA 1: MIGRAÇÃO ---
    print("\n[ETAPA 1 de 2] Migrando dados do Excel para o Banco de Dados...")
    try:
        migrar_dados()
        print("[ETAPA 1 CONCLUÍDA COM SUCESSO]")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO na etapa de migração: {e}")
        return # Para a execução se a migração falhar

    print("="*60)

    # --- ETAPA 2: GERAÇÃO DO DASHBOARD ---
    print("\n[ETAPA 2 de 2] Gerando o dashboard com os dados atualizados...")
    try:
        # O agente_autonomo.py já detecta a data automaticamente
        gerar_dashboard()
        print("[ETAPA 2 CONCLUÍDA COM SUCESSO]")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO na etapa de geração do dashboard: {e}")
        return

    print("="*60)
    print("\n🎉🎉🎉 PROCESSO COMPLETO! 🎉🎉🎉")
    print(f"Seu dashboard '{NOME_OUTPUT_HTML}' foi atualizado com sucesso.")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    executar_processo_completo()

# Versão final