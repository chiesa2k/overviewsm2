import os
import subprocess
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Garanta que os nomes dos seus scripts estão corretos
SCRIPT_MIGRACAO = "migracao_excel_db.py"
SCRIPT_AGENTE = "agente_autonomo.py"
# O caminho completo para a pasta do seu projeto. Use a letra do seu drive (C:, D:, etc.)
CAMINHO_PROJETO = r"C:\Users\andrey.chiesa\OneDrive - SUPPLY MARINE SERVICOS LTDA\Área de Trabalho\analista_dados"

def executar_comando(comando):
    """Executa um comando no terminal e mostra a saída em tempo real."""
    print(f"\n> Executando: {comando}")
    try:
        # 'cwd' (current working directory) garante que o comando é executado na pasta correta
        processo = subprocess.Popen(
            comando, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            cwd=CAMINHO_PROJETO
        )
        
        # Lê e imprime a saída do processo em tempo real
        while True:
            output = processo.stdout.readline()
            if output == '' and processo.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Verifica se houve erro
        if processo.returncode != 0:
            print(f"ERRO: O comando falhou com o código de saída {processo.returncode}")
            return False
        return True
    except FileNotFoundError:
        print(f"ERRO: O comando '{comando.split()[0]}' não foi encontrado. Verifique se o Python e o Git estão no PATH do sistema.")
        return False
    except Exception as e:
        print(f"ERRO inesperado ao executar o comando: {e}")
        return False

def processo_completo():
    """Orquestra a execução completa do processo de BI."""
    print("INICIANDO PROCESSO DE ATUALIZACAO COMPLETA DO DASHBOARD")
    print("="*60)

    # --- ETAPA 1: MIGRAÇÃO ---
    print("\n[ETAPA 1 de 3] Migrando dados do Excel para o Banco de Dados...")
    if not executar_comando(f"python {SCRIPT_MIGRACAO}"):
        return # Para a execução se a migração falhar

    # --- ETAPA 2: GERAÇÃO DO DASHBOARD ---
    print("\n[ETAPA 2 de 3] Gerando o dashboard com os dados atualizados...")
    if not executar_comando(f"python {SCRIPT_AGENTE}"):
        return

    # --- ETAPA 3: PUBLICAÇÃO NO GITHUB ---
    print("\n[ETAPA 3 de 3] Publicando a nova versão no GitHub...")
    commit_message = f"Atualizacao automatica do dashboard - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    comandos_git = f'git add . && git commit -m "{commit_message}" && git push'
    if not executar_comando(comandos_git):
        return

    print("="*60)
    print("\nPROCESSO COMPLETO!")
    print("Seu dashboard foi atualizado com sucesso.")

if __name__ == "__main__":
    processo_completo()
