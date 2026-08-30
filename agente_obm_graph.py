import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

# Carrega variáveis de ambiente
load_dotenv(find_dotenv(), override=True)
groq_key = os.getenv("GROQ_API_KEY", "").strip()

if not groq_key or not groq_key.startswith("gsk_"):
    print("\n[ERRO CRITICO] GROQ_API_KEY nao encontrada\n")
    sys.exit(1)

# Inicializa o LLM
llm = ChatGroq(model_name="qwen/qwen3.8-27b", temperature=0.1, groq_api_key=groq_key)
LEAN_EXEC = shutil.which("lean") or shutil.which("lake")
MEMORY_FILE = "banco_provas.json"


# --- ESTRUTURA DO ESTADO ---
class AgentState(TypedDict):
    problema: str
    categoria: str
    solucao_humana: str
    codigo_lean: str
    resultado_lean: str
    sucesso: bool
    tentativas: int
    max_tentativas: int
    exemplos_memoria: str


# --- FUNÇÕES AUXILIARES DE BANCO/MEMÓRIA ---
def me_carregar_memoria() -> List[Dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def me_salvar_prova_sucesso(problema: str, categoria: str, codigo_lean: str):
    memoria = me_carregar_memoria()
    if any(item.get("problema") == problema for item in memoria):
        return
    memoria.append(
        {
            "problema": problema,
            "categoria": categoria,
            "codigo_lean": codigo_lean,
        }
    )
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)
    print(f"\n[MEMORIA] Prova salva na categoria '{categoria}'!")


def me_buscar_provas_similares(categoria: str, limite: int = 2) -> str:
    memoria = me_carregar_memoria()
    similares = [
        item for item in memoria if item.get("categoria") == categoria
    ] or memoria[:limite]
    if not similares:
        return "Nenhuma demonstracao anterior nesta categoria."
    texto = "Exemplos de provas bem-sucedidas no banco de memoria:\n"
    for i, item in enumerate(similares, 1):
        texto += f"\n--- Exemplo {i} ({item.get('categoria')}) ---\nProblema: {item.get('problema')}\nCodigo Lean:\n{item.get('codigo_lean')}\n"
    return texto


def me_executar_lean(codigo_lean: str) -> tuple[bool, str]:
    if not LEAN_EXEC:
        return True, "Simulacao: Lean executado com sucesso."
    with tempfile.NamedTemporaryFile(
        suffix=".lean", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(codigo_lean)
        temp_path = f.name
    try:
        res = subprocess.run(
            [LEAN_EXEC, temp_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0 and "error" not in res.stderr.lower():
            return True, res.stdout or "Demonstracao verificada com sucesso."
        return False, res.stderr or res.stdout or "Erro Lean."
    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# --- NÓS DO GRAFO ---
def no_buscar_memoria(state: AgentState) -> Dict:
    print("\n--- [NO: Buscar Memoria] ---")
    return {
        "exemplos_memoria": me_buscar_provas_similares(state["categoria"])
    }


def no_gerar_solucao(state: AgentState) -> Dict:
    print(
        f"\n--- [NO: Gerar Solucao] Tentativa {state['tentativas'] + 1} ---"
    )
    p_sys = "Voce e um especialista em Lean 4. Gere APENAS o codigo dentro de ```lean ... ```."
    
    p_user = f"Problema: {state['problema']}\nCategoria: {state['categoria']}\n"
    
    if state.get("solucao_humana"):
        p_user += f"Solucao/Dica de referencia fornecida pelo usuario: {state['solucao_humana']}\n"

    p_user += f"\n{state['exemplos_memoria']}"

    if state.get("resultado_lean") and not state["sucesso"]:
        p_user += f"\nErro anterior:\n{state['resultado_lean']}\nCorrija."

    res = llm.invoke(
        [SystemMessage(content=p_sys), HumanMessage(content=p_user)]
    )
    c = res.content
    code = (
        c.split("```lean")[1].split("```")[0].strip()
        if "```lean" in c
        else c
    )
    return {"codigo_lean": code, "tentativas": state["tentativas"] + 1}


def no_validar_lean(state: AgentState) -> Dict:
    print("\n--- [NO: Validar Lean] ---")
    ok, msg = me_executar_lean(state["codigo_lean"])
    print(f"Resultado: {'SUCESSO' if ok else 'FALHA'}")
    return {"sucesso": ok, "resultado_lean": msg}


def no_salvar_aprendizado(state: AgentState) -> Dict:
    print("\n--- [NO: Salvar Aprendizado] ---")
    me_salvar_prova_sucesso(
        state["problema"], state["categoria"], state["codigo_lean"]
    )
    return {}


def checar_sucesso(state: AgentState) -> str:
    if state["sucesso"]:
        return "salvar_aprendizado"
    if state["tentativas"] >= state["max_tentativas"]:
        return "fim"
    return "gerar_solucao"


# --- MONTAGEM DO GRAFO ---
wf = StateGraph(AgentState)

wf.add_node("buscar_memoria", no_buscar_memoria)
wf.add_node("gerar_solucao", no_gerar_solucao)
wf.add_node("validar_lean", no_validar_lean)
wf.add_node("salvar_aprendizado", no_salvar_aprendizado)

wf.set_entry_point("buscar_memoria")
wf.add_edge("buscar_memoria", "gerar_solucao")
wf.add_edge("gerar_solucao", "validar_lean")
wf.add_conditional_edges(
    "validar_lean",
    checar_sucesso,
    {
        "salvar_aprendizado": "salvar_aprendizado",
        "gerar_solucao": "gerar_solucao",
        "fim": END,
    },
)
wf.add_edge("salvar_aprendizado", END)

# COMPILAÇÃO DO GRAFO (Exporta a variável 'app')
app = wf.compile()

if __name__ == "__main__":
    init = {
        "problema": "Prove que para todo inteiro n, n + 0 = n.",
        "categoria": "Aritmetica",
        "solucao_humana": "",
        "codigo_lean": "",
        "resultado_lean": "",
        "sucesso": False,
        "tentativas": 0,
        "max_tentativas": 3,
        "exemplos_memoria": "",
    }
    print("\n=== INICIANDO AGENTE OBM ===")
    out = app.invoke(init)
    print(f"\nSucesso: {out['sucesso']}\nCodigo:\n{out['codigo_lean']}")
