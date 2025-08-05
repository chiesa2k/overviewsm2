import os
import shutil
import subprocess
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Onde seu arquivo Excel original está (na sua pasta do OneDrive)
CAMINHO_ONEDRIVE = r"C:\Users\andrey.chiesa\OneDrive - SUPPLY MARINE SERVICOS LTDA\Área de Trabalho\analista_dados"
NOME_ARQUIVO_EXCEL = "SM_Gerenciamento_19_20 (6).xlsx"

# A nova "oficina" do nosso robô, fora do OneDrive
PASTA_TRABALHO = r"C:\automacao_dashboard"
URL_REPOSITORIO_GIT = "https://github.com/chiesa2k/overviewsm2.git"

def executar_comando(comando, pasta_execucao):
    """Executa um comando no terminal dentro da pasta de trabalho especificada."""
    print(f"\n> Executando em '{pasta_execucao}': {comando}")
    try:
        processo = subprocess.Popen(
            comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, encoding='utf-8', errors='replace', cwd=pasta_execucao
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

def preparar_ambiente():
    """Garante que a pasta de trabalho existe, é um repositório Git e tem os arquivos mais recentes."""
    print("\n[ETAPA 1 de 4] Preparando o ambiente de automacao...")
    
    # 1. Verifica se a pasta de trabalho existe
    if not os.path.exists(PASTA_TRABALHO):
        print(f"Pasta de trabalho nao encontrada. Clonando o repositorio para '{PASTA_TRABALHO}'...")
        if not executar_comando(f'git clone {URL_REPOSITORIO_GIT} "{PASTA_TRABALHO}"', None):
            return False
    
    # 2. Copia o arquivo Excel mais recente
    print(f"- Copiando {NOME_ARQUIVO_EXCEL} para a pasta de trabalho...")
    origem_excel = os.path.join(CAMINHO_ONEDRIVE, NOME_ARQUIVO_EXCEL)
    destino_excel = os.path.join(PASTA_TRABALHO, NOME_ARQUIVO_EXCEL)
    if os.path.exists(origem_excel):
        shutil.copy2(origem_excel, destino_excel)
    else:
        print(f"ERRO: Arquivo Excel '{origem_excel}' nao encontrado.")
        return False
        
    return True

def processo_completo():
    """Orquestra a execução completa do processo de BI."""
    print("INICIANDO PROCESSO DE ATUALIZACAO COMPLETA DO DASHBOARD")
    print("="*60)

    if not preparar_ambiente():
        return

    print("\n[ETAPA 2 de 4] Migrando dados do Excel para o Banco de Dados...")
    if not executar_comando(f"python migracao_excel_db.py", PASTA_TRABALHO):
        return

    print("\n[ETAPA 3 de 4] Gerando o dashboard com os dados atualizados...")
    if not executar_comando(f"python agente_autonomo.py", PASTA_TRABALHO):
        return

    print("\n[ETAPA 4 de 4] Publicando a nova versao no GitHub...")
    commit_message = f"Atualizacao automatica do dashboard - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    comandos_git = f'git add . && git commit -m "{commit_message}" && git push'
    if not executar_comando(comandos_git, PASTA_TRABALHO):
        return

    print("="*60)
    print("\nPROCESSO COMPLETO!")
    print("Seu dashboard foi atualizado com sucesso.")

if __name__ == "__main__":
    processo_completo()
