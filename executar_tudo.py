import os
import subprocess
from datetime import datetime

# --- CONFIGURAÇÃO ---
SCRIPT_MIGRACAO = "migracao_excel_db.py"
SCRIPT_AGENTE = "agente_autonomo.py"
CAMINHO_PROJETO = r"C:\Users\andrey.chiesa\OneDrive - SUPPLY MARINE SERVICOS LTDA\Área de Trabalho\analista_dados"

def executar_comando(comando):
    """Executa um comando no terminal e mostra a saída em tempo real."""
    print(f"\n> Executando: {comando}")
    try:
        processo = subprocess.Popen(
            comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, encoding='utf-8', errors='replace', cwd=CAMINHO_PROJETO
        )
        while True:
            output = processo.stdout.readline()
            if output == '' and processo.poll() is not None:
                break
            if output:
                print(output.strip())
        if processo.returncode != 0:
            print(f"ERRO: O comando falhou com o codigo de saida {processo.returncode}")
            return False
        return True
    except Exception as e:
        print(f"ERRO inesperado ao executar o comando: {e}")
        return False

def processo_completo():
    """Orquestra a execução completa do processo de BI."""
    print("INICIANDO PROCESSO DE ATUALIZACAO COMPLETA DO DASHBOARD")
    print("="*60)

    print("\n[ETAPA 1 de 3] Migrando dados do Excel para o Banco de Dados...")
    if not executar_comando(f"python {SCRIPT_MIGRACAO}"):
        return

    print("\n[ETAPA 2 de 3] Gerando o dashboard com os dados atualizados...")
    if not executar_comando(f"python {SCRIPT_AGENTE}"):
        return

    print("\n[ETAPA 3 de 3] Publicando a nova versao no GitHub...")
    commit_message = f"Atualizacao automatica do dashboard - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    comandos_git = f'git add . && git commit -m "{commit_message}" && git push'
    if not executar_comando(comandos_git):
        return

    print("="*60)
    print("\nPROCESSO COMPLETO!")
    print("Seu dashboard foi atualizado com sucesso.")

if __name__ == "__main__":
    processo_completo()
