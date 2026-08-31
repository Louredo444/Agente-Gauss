import os
import sys
import time
import json
import logging
from typing import List, Literal
from pydantic import BaseModel, Field, ValidationError
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ARQUIVO_BANCO = "banco_provas.json"

class ProblemaOlimpiada(BaseModel):
    id: str = Field(..., description="ID no formato COMPETICAO_ANO_NUMERO")
    competicao: str
    ano: int
    fase_ou_nivel: str
    categoria: Literal["Algebra", "Combinatoria", "Geometria", "Teoria dos Numeros"]
    topicos: List[str]
    dificuldade_estimada: str
    enunciado: str
    solucao: str
    fonte_url: str
    tags: List[str]

SYSTEM_PROMPT_INGESTOR = """
Você é o Lagrange, agente automatizado de estruturação de dados matemáticos.
Sua tarefa é converter problemas brutos de olimpíadas em um JSON estrito.

Regras:
1. Sintaxe LaTeX: Inline usa $...$ e Bloco usa $$...$$.
2. Responda APENAS o JSON puro, sem marcações adicionais ou textos explicativos.
"""

def carregar_banco() -> list:
    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar {ARQUIVO_BANCO}: {e}")
            return []
    return []

def salvar_banco(dados: list):
    try:
        with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        logging.info(f"Banco atualizado. Total de problemas: {len(dados)}")
    except Exception as e:
        logging.error(f"Erro ao salvar banco JSON: {e}")

def processar_com_validacao(llm, texto_bruto: str) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_INGESTOR),
        HumanMessage(content=f"Estruture o seguinte problema:\n\n{texto_bruto}")
    ]
    try:
        resposta = llm.invoke(messages)
        conteudo = resposta.content.strip()
        
        if conteudo.startswith("```json"):
            conteudo = conteudo[7:]
        if conteudo.startswith("```"):
            conteudo = conteudo[3:]
        if conteudo.endswith("```"):
            conteudo = conteudo[:-3]
            
        dados_dict = json.loads(conteudo.strip())
        problema_validado = ProblemaOlimpiada(**dados_dict)
        return problema_validado.model_dump()
    except ValidationError as ve:
        logging.error(f"Erro de validação no Schema Pydantic: {ve}")
        return None
    except Exception as e:
        logging.error(f"Erro no processamento da LLM: {e}")
        return None

def executar_ciclo(llm):
    logging.info("Iniciando ciclo de ingestão...")
    banco = carregar_banco()
    ids_existentes = {item.get("id") for item in banco if "id" in item}

    entradas_brutas = [
        "OBM 2023 Nível 3 P1: Seja ABCD um quadrilátero cíclico...",
        "IMO 2022 P1: Determine todas as funções f: R -> R..."
    ]

    novos_itens = 0
    for texto in entradas_brutas:
        item_validado = processar_com_validacao(llm, texto)
        if item_validado:
            if item_validado["id"] not in ids_existentes:
                banco.append(item_validado)
                ids_existentes.add(item_validado["id"])
                novos_itens += 1
                logging.info(f"Problema {item_validado['id']} validado e adicionado.")
            else:
                logging.info(f"Problema {item_validado['id']} já existe no banco.")

    if novos_itens > 0:
        salvar_banco(banco)

def main():
    logging.info("=== INICIANDO AGENTE LAGRANGE (MODO RESILIENTE 24 HORAS) ===")
    
    if not GROQ_API_KEY:
        logging.error("GROQ_API_KEY não encontrada nas variáveis de ambiente. Encerrando.")
        sys.exit(1)

    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY)
    
    tempo_inicio = time.time()
    duracao_maxima = 86400  # 24 horas em segundos
    intervalo_loop = 3600   # 1 hora entre as execuções
    
    while (time.time() - tempo_inicio) < duracao_maxima:
        try:
            logging.info("Executando ciclo de ingestão...")
            executar_ciclo(llm)
        except Exception as e:
            logging.error(f"❌ Ocorreu uma falha no ciclo atual: {e}. O Lagrange continuará ativo.")

        logging.info(f"Aguardando {intervalo_loop // 60} minutos para o próximo ciclo...")
        time.sleep(intervalo_loop)

    logging.info("=== FIM DA EXECUÇÃO DE 24 HORAS DO LAGRANGE ===")

if __name__ == "__main__":
    main()
