import os
import sys
import time
import json
import logging
import datetime
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Configuração de Logs para monitoramento na Aba 4 do Streamlit
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ARQUIVO_BANCO = "banco_provas.json"

SYSTEM_PROMPT_INGESTOR = """
Você é o **Lagrange**, agente automatizado de estruturação de dados matemáticos.
Sua tarefa é receber problemas brutos de olimpíadas de matemática (OBM, IMO, AoPS) e convertê-los estritamente em um JSON válido.

Regras:
1. Sintaxe LaTeX: Use $...$ para fórmulas inline e $$...$$ para equações em bloco.
2. Escapes no JSON: Use barras invertidas duplas (\\\\) para comandos LaTeX (ex: \\\\mathbb{R}).
3. Categorias permitidas: Algebra, Combinatoria, Geometria, Teoria dos Numeros.

Saída esperada (Apenas JSON):
{
  "id": "COMPETICAO_ANO_NUMERO",
  "competicao": "Nome da Competição",
  "ano": 2024,
  "fase_ou_nivel": "Fase / Nível / Shortlist",
  "categoria": "Algebra | Combinatoria | Geometria | Teoria dos Numeros",
  "topicos": ["Tópico 1", "Tópico 2"],
  "dificuldade_estimada": "Fácil | Média | Difícil | Medalha de Ouro",
  "enunciado": "Texto do enunciado formatado em LaTeX...",
  "solucao": "Solução completa formatada em LaTeX...",
  "fonte_url": "URL original ou fonte",
  "tags": ["LaTeX Validado"]
}
"""

def carregar_banco():
    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar {ARQUIVO_BANCO}: {e}")
            return []
    return []

def salvar_banco(dados):
    try:
        with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        logging.info(f"Banco atualizado com sucesso. Total de problemas: {len(dados)}")
    except Exception as e:
        logging.error(f"Erro ao salvar no arquivo JSON: {e}")

def processar_problema_com_llm(llm, texto_bruto):
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_INGESTOR),
            HumanMessage(content=f"Estruture o seguinte problema:\n\n{texto_bruto}")
        ]
        resposta = llm.invoke(messages)
        conteudo = resposta.content.strip()
        
        # Limpeza rápida de blocos de código markdown se houver
        if conteudo.startswith("```json"):
            conteudo = conteudo[7:]
        if conteudo.startswith("```"):
            conteudo = conteudo[3:]
        if conteudo.endswith("```"):
            conteudo = conteudo[:-3]
            
        dados_json = json.loads(conteudo.strip())
        return dados_json
    except Exception as e:
        logging.error(f"Falha ao processar texto com LLM: {e}")
        return None

def executar_ciclo_ingestao(llm):
    logging.info("Iniciando varredura e ingestão de novos problemas...")
    banco = carregar_banco()
    
    # Exemplo de fila de itens para ingestão (Pode ser substituído por web scraping do AoPS/OBM)
    fila_exemplo = [
        "OBM 2023 Nível 3 P1: Seja ABCD um quadrilátero cíclico. Prove que as bissetrizes...",
        "IMO 2022 P1: Determine todas as funções f: R -> R tais que f(x + y) = f(x) + f(y)..."
    ]
    
    novos_itens = 0
    for item in fila_exemplo:
        logging.info(f"Processando entrada: {item[:40]}...")
        resultado = processar_problema_com_llm(llm, item)
        if resultado:
            # Evita duplicatas pelo ID
            if not any(p.get("id") == resultado.get("id") for p in banco):
                banco.append(resultado)
                novos_itens += 1
                logging.info(f"Problema {resultado.get('id')} adicionado com sucesso.")
            else:
                logging.info(f"Problema {resultado.get('id')} já existe no banco.")
                
    if novos_itens > 0:
        salvar_banco(banco)
    else:
        logging.info("Nenhum item novo adicionado neste ciclo.")

def main():
    logging.info("=== INICIANDO AGENTE LAGRANGE (MODO 24 HORAS) ===")
    
    if not GROQ_API_KEY:
        logging.error("GROQ_API_KEY não encontrada nas variáveis de ambiente. Encerrando.")
        sys.exit(1)
        
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY)
    
    tempo_inicio = time.time()
    duracao_maxima = 86400  # 24 horas em segundos
    intervalo_loop = 3600   # Executa a cada 1 hora
    
    while (time.time() - tempo_inicio) < duracao_maxima:
        try:
            executar_ciclo_ingestao(llm)
        except Exception as e:
            logging.error(f"Erro crítico no loop de execução: {e}")
            
        logging.info(f"Aguardando {intervalo_loop // 60} minutos para a próxima varredura...")
        time.sleep(intervalo_loop)
        
    logging.info("=== FIM DA EXECUÇÃO DE 24 HORAS DO LAGRANGE ===")

if __name__ == "__main__":
    main()
