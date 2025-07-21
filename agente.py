import os
import pandas as pd
import sqlite3
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (GOOGLE_API_KEY)
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. CONFIGURAÇÃO ---
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
except Exception as e:
    print(f"Erro ao inicializar o modelo. Verifique sua 'GOOGLE_API_KEY'.")
    exit()

NOME_BANCO_DADOS = "gerenciamento.db"

# --- 2. FUNÇÕES DE SUPORTE ---
def executar_consulta_sql(query: str) -> str:
    """Executa uma consulta SQL no banco de dados e retorna o resultado como texto."""
    print(f"\n--- Executando a query: [{query}] ---")
    try:
        conexao = sqlite3.connect(NOME_BANCO_DADOS)
        df = pd.read_sql_query(query, conexao)
        conexao.close()
        if df.empty:
            return "A consulta não retornou nenhum resultado."
        return df.to_string()
    except Exception as e:
        return f"Erro ao executar a consulta SQL: {e}."

def limpar_saida_sql(sql_code: str) -> str:
    """
    Limpa a saída da IA para isolar e retornar apenas a primeira declaração SQL válida.
    """
    # Encontra o início da declaração SQL (ignorando maiúsculas/minúsculas)
    start_pos = sql_code.upper().find("SELECT")
    if start_pos == -1:
        return "ERRO: A IA não gerou uma query SQL com 'SELECT'."
        
    # Isola a string a partir do 'SELECT'
    sql_from_select = sql_code[start_pos:]
    
    # Encontra o final da declaração SQL (o ponto e vírgula)
    end_pos = sql_from_select.find(";")
    if end_pos != -1:
        # Se encontrou um ';', retorna tudo até ele
        return sql_from_select[:end_pos].strip()
    else:
        # Se não encontrou ';', apenas limpa e retorna a string
        return sql_from_select.strip()


# --- 3. O PROMPT INTELIGENTE ---
schema_tabela_vendas_limpo = [
    'ATENDIMENTO (ANDAMENTO)', 'ATENDIMENTO (Nº)', 'ATENDIMENTO (TIPO)', 'ATENDIMENTO (REAGENDAMENTO)', 'DATA (ABERTURA)', 'EMISSOR', 'CLIENTE (NOME)', 'CLIENTE (UNIDADE)', 'SERVIÇO (REGIME)', 'SERVIÇO (LOCAL)', 'CLIENTE (SOLICITANTE)', 'CLIENTE (FUNÇÃO)', 'CLIENTE (TELEFONE)', 'CLIENTE (EMAIL)', 'CLIENTE (COMPRADOR)', 'CLIENTE (FUNÇÃO2)', 'CLIENTE (TELEFONE2)', 'CLIENTE (EMAIL2)', 'SERVIÇO (TIPO)', 'SERVIÇO (DESCRIÇÃO)', 'DOCUMENTO', 'REF DOCUMENTO', 'REVISÃO', 'DATA (ENVIO PROPOSTA)', 'VALIDADE', 'PRAZO (EM DIAS)', 'INDICADOR DE QUALIDADE', 'ATENDIMENTO (STATUS)', 'ATENDimento (MOTIVO - ANDAMENTO)', 'RELATÓRIO DE AVALIAÇÃO', 'DATA (INÍCIO ATENDIMENTO)', 'REAGENDADO PARA:', 'DATA (PREVISÃO DE TÉRMINO)', 'DATA (FINAL ATENDIMENTO)', 'DATA (ENVIO DOS RELATÓRIOS)', 'DATA (LIBERAÇÃO BM)', 'DATA (RECEBIMENTO PO)', 'Nº PO', 'VALOR - VENDA (SERVIÇO)', 'VALOR - VENDA (CONSUMÍVEIS)', 'VALOR - VENDA (MOBILIZAÇÃO)', 'VALOR - VENDA (MATERIAIS)', 'VALOR - VENDA (TOTAL)', 'DESC (DESCONTO %)', 'VALOR - VENDA (SERVIÇO) DESC.', 'VALOR - VENDA (CONSUMÍVEIS) DESC.', 'VALOR - VENDA (MOBILIZAÇÃO) DESC.', 'VALOR - VENDA (MATERIAIS) DESC.', 'VALOR - VENDA (TOTAL) DESC.', 'VALOR - COMPRA (SERVIÇO)', 'VALOR - COMPRA (MATERIAIS)', 'VALOR - COMPRA (TOTAL)', 'Nº NOTA FISCAL', 'DATA (FATURAMENTO)', 'DATA (PRAZO - PAGAMENTO)', 'DATA (RECEBimento)', '(AUX) STATUS (REALIZADO)', '(AUX) STATUS (DATA RECEBIMENTO)', '(AUX) DATA (PRAZO PAGAMENTO - DIAS)', '(AUX) SERVIÇO (BUDGET)', '(AUX) SERVIÇO (CONTRATO)', '(AUX) SERVIÇO (CONTRATO)2', '(AUX) SERVIÇO (CONTRATO)3', '(AUX) SERVIÇO (CONTRATO)4'
]
schema_str = ', '.join(f'"{col}"' for col in schema_tabela_vendas_limpo)

# PROMPT ATUALIZADO COM AS DUAS LÓGICAS DE NEGÓCIO
prompt_sql_translator = ChatPromptTemplate.from_messages(
    [
        ("system", f"""Você é um especialista em SQL que traduz perguntas em queries para um banco de dados SQLite.

        **REGRAS DE NEGÓCIO OBRIGATÓRIAS:**
        Primeiro, identifique se o usuário está perguntando sobre "FATURAMENTO" ou sobre "VENDAS". Use a regra apropriada:

        **REGRA 1: Se a pergunta for sobre FATURAMENTO:**
        - **Filtro de Status:** A query DEVE incluir a cláusula `WHERE "ATENDIMENTO (ANDAMENTO)" IN ('Finalizado', 'Finalizado Com Faturamento')`.
        - **Coluna de Data:** A coluna para filtrar por data é `"DATA (FATURAMENTO)"`.
        - **Coluna de Valor:** A coluna para somar faturamento é `"VALOR - VENDA (TOTAL) DESC."`.

        **REGRA 2: Se a pergunta for sobre VENDAS:**
        - **Filtro de Status:** NÃO APLIQUE NENHUM FILTRO na coluna "ATENDIMENTO (ANDAMENTO)".
        - **Coluna de Data:** A coluna para filtrar por data é `"DATA (RECEBIMENTO PO)"`.
        - **Coluna de Valor:** A coluna para somar o valor das vendas é `"VALOR - VENDA (TOTAL) DESC."`.

        **REGRAS GERAIS DE SINTAXE SQL:**
        - Para filtrar por ano, use `strftime('%Y', NOME_DA_COLUNA_DE_DATA) = 'ANO'`.
        - Nomes de colunas com espaços ou caracteres especiais DEVEM estar entre aspas duplas (").
        - **Sua única saída deve ser o código SQL puro. Não adicione nenhum outro texto ou explicação.**

        ESQUEMA DA TABELA 'Vendas':
        {schema_str}
        """),
        ("human", "{question}"),
    ]
)

prompt_final_answer = ChatPromptTemplate.from_messages(
    [
        ("system", "Você é um assistente prestativo que resume resultados de banco de dados em uma frase clara e amigável em português."),
        ("human", "Baseado nesta pergunta '{question}' e neste resultado de banco de dados '{result}', por favor, me dê uma resposta final."),
    ]
)

# --- 4. O FLUXO (CHAIN) ---
sql_chain = prompt_sql_translator | llm | StrOutputParser() | limpar_saida_sql
final_chain = prompt_final_answer | llm | StrOutputParser()

# --- 5. EXECUÇÃO ---
if __name__ == "__main__":
    print("🤖 Agente Biespecializado (Faturamento e Vendas) v7.1 iniciado.")
    print("-" * 30)
    while True:
        pergunta = input("Sua pergunta: ")
        if pergunta.lower() == 'sair':
            break
        
        try:
            print("\n1. Traduzindo pergunta para SQL...")
            generated_sql = sql_chain.invoke({"question": pergunta})
            
            sql_result = executar_consulta_sql(generated_sql)
            print(f"\n2. Resultado do banco de dados:\n{sql_result}")
            
            if "Erro" in sql_result:
                print("\nRESPOSTA DO AGENTE:")
                print("Não foi possível gerar uma resposta pois a consulta ao banco de dados falhou.")
            else:
                print("\n3. Gerando resposta final...")
                final_answer = final_chain.invoke({"question": pergunta, "result": sql_result})
                
                print("\nRESPOSTA DO AGENTE:")
                print(final_answer)

        except Exception as e:
            print(f"\nOcorreu um erro durante a execução: {e}")
        
        print("-" * 30)

