import os
import shutil
import subprocess
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Onde seus arquivos originais estão (sua pasta de trabalho principal)
PASTA_ORIGEM = r"C:\Users\andrey.chiesa\OneDrive - SUPPLY MARINE SERVICOS LTDA\Área de Trabalho\analista_dados"

# A "oficina" do nosso robô, fora do OneDrive
PASTA_TRABALHO = r"C:\automacao_dashboard"

# Nomes dos arquivos que o robô precisa para trabalhar
ARQUIVOS_NECESSARIOS = [
    "migracao_excel_db.py",
    "agente_autonomo.py",
    "dashboard_template.html",
    "SM_Gerenciamento_19_20 (6).xlsx",
    ".env"
]

def preparar_ambiente():
    """Copia os arquivos mais recentes da pasta de origem para a de trabalho."""
    print("\n[ETAPA 1 de 4] Preparando o ambiente de automacao...")
    if not os.path.exists(PASTA_TRABALHO):
        print(f"ERRO: A pasta de trabalho '{PASTA_TRABALHO}' nao foi encontrada.")
        print("Por favor, execute o 'git clone' conforme o guia.")
        return False

    print(f"- Copiando arquivos essenciais para a pasta de trabalho...")
    for nome_arquivo in ARQUIVOS_NECESSARIOS:
        origem = os.path.join(PASTA_ORIGEM, nome_arquivo)
        destino = os.path.join(PASTA_TRABALHO, nome_arquivo)
        if os.path.exists(origem):
            shutil.copy2(origem, destino)
        else:
            print(f"AVISO: Arquivo '{nome_arquivo}' nao encontrado na origem.")
            
    return True

def executar_comando(comando, pasta):
    """Executa um comando no terminal dentro da pasta de trabalho especificada."""
    print(f"\n> Executando em '{pasta}': {comando}")
    try:
        processo = subprocess.Popen(
            comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, encoding='utf-8', errors='replace', cwd=pasta
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
