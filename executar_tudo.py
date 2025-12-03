import os
import subprocess
import shutil
from datetime import datetime
import sys

# --- CONFIGURAÇÃO (CAMINHOS FIXOS) ---
# A "oficina" onde o robô trabalha e onde está o ambiente virtual (venv)
PASTA_TRABALHO = r"C:\automacao_dashboard"

# A pasta do seu projeto no Desktop (onde está o Git e os arquivos originais)
PASTA_PROJETO_ORIGEM = r"C:\Users\pc\Desktop\analista_dados\analista_dados\overviewsm2"

# Lista de arquivos que devem ser copiados da origem para a oficina
ARQUIVOS_ESSENCIAIS = [
    "migracao_excel_db.py",
    "agente_autonomo.py",
    "dashboard_template.html",
    ".env",
    "SM_Gerenciamento_19_20 (6).xlsx" # Este arquivo DEVE estar na pasta do Desktop!
]

# Caminho do Python DENTRO da oficina
PYTHON_EXECUTAVEL = os.path.join(PASTA_TRABALHO, "venv", "Scripts", "python.exe")

# --- FUNÇÕES AUXILIARES ---

def executar_comando(comando: str, pasta_execucao: str = None):
    """Executa um comando no terminal, forçando UTF-8 para evitar erros de acentuação."""
    print(f"\n> Executando em '{pasta_execucao or '.'}': {comando}")
    try:
        # Configura variáveis de ambiente para forçar UTF-8
        env_vars = os.environ.copy()
        env_vars['PYTHONIOENCODING'] = 'utf-8'
        env_vars['PYTHONUTF8'] = '1'

        processo = subprocess.run(
            comando,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=pasta_execucao,
            env=env_vars
        )
        if processo.stdout:
            print("Saída Padrão:")
            print(processo.stdout)
        if processo.stderr:
            print("Saída de Aviso/Erro:")
            print(processo.stderr)

    except subprocess.CalledProcessError as e:
        print(f"ERRO CRÍTICO: O comando falhou com código {e.returncode}", file=sys.stderr)
        if e.stdout: print(e.stdout, file=sys.stderr)
        if e.stderr: print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRO inesperado: {e}", file=sys.stderr)
        sys.exit(1)

# --- FLUXO PRINCIPAL ---

if __name__ == "__main__":
    print("INICIANDO PROCESSO - MÁQUINA PESSOAL (AUTO-CONFIGURAÇÃO)")
    print(f"Origem (Git): {PASTA_PROJETO_ORIGEM}")
    print(f"Destino (Oficina): {PASTA_TRABALHO}")
    print("=" * 60)

    # ETAPA 1: Preparar o Ambiente
    print("\n[ETAPA 1] Preparando a oficina...")
    os.makedirs(PASTA_TRABALHO, exist_ok=True)
    
    # Verificação e Criação Automática do Ambiente Virtual
    if not os.path.exists(PYTHON_EXECUTAVEL):
        print(f"AVISO: Python dedicado não encontrado em {PYTHON_EXECUTAVEL}")
        print("Criando ambiente virtual (venv) automaticamente...")
        try:
            # Usa o python do sistema para criar o venv
            subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=PASTA_TRABALHO, check=True)
            print("Ambiente virtual criado com sucesso!")
        except Exception as e:
            print(f"ERRO FATAL ao criar venv: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Instalação Automática de Dependências
    print("- Verificando e instalando bibliotecas necessárias...")
    pip_executavel = os.path.join(PASTA_TRABALHO, "venv", "Scripts", "pip.exe")
    try:
        # Tenta instalar/atualizar as libs. Se já existirem, é rápido.
        subprocess.run(
            [pip_executavel, "install", "pandas", "openpyxl", "python-dotenv"],
            check=True,
            capture_output=True 
        )
        print("Bibliotecas (pandas, openpyxl, dotenv) verificadas/instaladas com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"AVISO: Problema na instalação das bibliotecas. Tentando continuar... Erro: {e}")

    print("\n- Copiando arquivos recentes...")
    for nome_arquivo in ARQUIVOS_ESSENCIAIS:
        caminho_origem = os.path.join(PASTA_PROJETO_ORIGEM, nome_arquivo)
        caminho_destino = os.path.join(PASTA_TRABALHO, nome_arquivo)
        
        if os.path.exists(caminho_origem):
            try:
                shutil.copy(caminho_origem, caminho_destino)
                print(f"  OK: {nome_arquivo} copiado.")
            except Exception as e:
                print(f"  ERRO ao copiar {nome_arquivo}: {e}")
        else:
            print(f"  AVISO: Arquivo '{nome_arquivo}' não encontrado na origem.")
            if nome_arquivo.endswith(".xlsx"):
                print(f"  IMPORTANTE: O arquivo Excel PRECISA estar em: {PASTA_PROJETO_ORIGEM}")

    # ETAPA 2: Migrar os Dados
    print("\n[ETAPA 2] Migrando dados...")
    executar_comando(f'"{PYTHON_EXECUTAVEL}" migracao_excel_db.py', pasta_execucao=PASTA_TRABALHO)
    
    # ETAPA 3: Gerar o Dashboard
    print("\n[ETAPA 3] Gerando dashboard...")
    executar_comando(f'"{PYTHON_EXECUTAVEL}" agente_autonomo.py', pasta_execucao=PASTA_TRABALHO)
    
    # ETAPA 4: Publicar no GitHub
    print("\n[ETAPA 4] Publicando no GitHub...")
    
    caminho_html_gerado = os.path.join(PASTA_TRABALHO, "index.html")
    caminho_html_git = os.path.join(PASTA_PROJETO_ORIGEM, "index.html")
    
    if os.path.exists(caminho_html_gerado):
        # 1. Copia o HTML novo de volta para a pasta do Git
        try:
            shutil.copy(caminho_html_gerado, caminho_html_git)
            print("- Index.html atualizado copiado de volta para a pasta do projeto.")
            
            # 2. Executa os comandos Git na pasta do projeto original
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            cmd_git = f'git pull && git add . && git commit -m "Auto Update {data_hora}" && git push'
            executar_comando(cmd_git, pasta_execucao=PASTA_PROJETO_ORIGEM)
        except Exception as e:
            print(f"ERRO na etapa do Git: {e}")
            # Não damos exit(1) aqui para que o n8n considere sucesso se o dashboard foi gerado, mesmo se o git falhar
    else:
        print("ERRO CRÍTICO: O index.html não foi gerado na oficina.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("SUCESSO TOTAL!")