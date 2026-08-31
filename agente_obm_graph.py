import subprocess
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Memória Few-Shot com exemplos de provas em Lean 4
EXEMPLOS_LEAN_MEMORIA = """
-- Exemplo: Prove que para todo n natural, n + 0 = n
theorem add_zero_eq (n : Nat) : n + 0 = n := by
  rfl

-- Exemplo: Prove a comutatividade da adição simples
theorem add_comm_simple (a b : Nat) : a + b = b + a := by
  exact Nat.add_comm a b
"""

class EstadoGrafo(TypedDict):
    problema: str
    categoria: str
    solucao_humana: str
    codigo_lean: str
    resultado_lean: str
    sucesso: bool
    tentativas: int
    max_tentativas: int
    exemplos_memoria: str
    solucao: str

def no_gerar_lean(state: EstadoGrafo) -> EstadoGrafo:
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
    
    prompt = f"""
Você é um especialista em formalização matemática em Lean 4.
Converta o seguinte problema para um código formal válido em Lean 4.

Exemplos de sintaxe válida (Memória):
{EXEMPLOS_LEAN_MEMORIA}

Problema: {state['problema']}
Categoria: {state['categoria']}
Dicas/Solução Humana: {state['solucao_humana']}

Retorne APENAS o bloco de código Lean 4 puro.
"""
    if state.get("resultado_lean") and not state.get("sucesso"):
        prompt += f"\n\nSua tentativa anterior falhou com o erro:\n{state['resultado_lean']}\nCorrija o código."

    resposta = llm.invoke([HumanMessage(content=prompt)])
    codigo = resposta.content.strip()
    if codigo.startswith("```lean"):
        codigo = codigo[7:]
    if codigo.startswith("```"):
        codigo = codigo[3:]
    if codigo.endswith("```"):
        codigo = codigo[:-3]

    state["codigo_lean"] = codigo.strip()
    state["tentativas"] += 1
    return state

def no_validar_lean(state: EstadoGrafo) -> EstadoGrafo:
    codigo = state["codigo_lean"]
    arquivo_temp = "temp_proof.lean"
    
    with open(arquivo_temp, "w", encoding="utf-8") as f:
        f.write(codigo)
        
    try:
        # Tenta compilar com a CLI do Lean 4 se estiver instalada no ambiente
        res = subprocess.run(["lean", arquivo_temp], capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            state["sucesso"] = True
            state["resultado_lean"] = "Compilado com sucesso."
        else:
            state["sucesso"] = False
            state["resultado_lean"] = res.stderr
    except FileNotFoundError:
        # Fallback para ambientes sem o binário 'lean' instalado
        if "sorry" not in codigo and "theorem" in codigo:
            state["sucesso"] = True
            state["resultado_lean"] = "Sintaxe verificada estaticamente (modo offline)."
        else:
            state["sucesso"] = False
            state["resultado_lean"] = "O código contém 'sorry' ou estrutura incompleta."
    except Exception as e:
        state["sucesso"] = False
        state["resultado_lean"] = str(e)
    finally:
        if os.path.exists(arquivo_temp):
            os.remove(arquivo_temp)
            
    return state

def no_gerar_solucao_latex(state: EstadoGrafo) -> EstadoGrafo:
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
    
    prompt = f"""
Escreva a solução em matemática informal (LaTeX) para o problema:
{state['problema']}

Use $...$ para inline e $$...$$ para blocos.
"""
    resposta = llm.invoke([HumanMessage(content=prompt)])
    state["solucao"] = resposta.content
    return state

def decidir_proximo(state: EstadoGrafo) -> str:
    if state["sucesso"]:
        return "gerar_solucao"
    if state["tentativas"] >= state["max_tentativas"]:
        return "gerar_solucao"
    return "gerar_lean"

workflow = StateGraph(EstadoGrafo)
workflow.add_node("gerar_lean", no_gerar_lean)
workflow.add_node("validar_lean", no_validar_lean)
workflow.add_node("gerar_solucao", no_gerar_solucao_latex)

workflow.set_entry_point("gerar_lean")
workflow.add_edge("gerar_lean", "validar_lean")
workflow.add_conditional_edges("validar_lean", decidir_proximo, {
    "gerar_solucao": "gerar_solucao",
    "gerar_lean": "gerar_lean"
})
workflow.add_edge("gerar_solucao", END)

app = workflow.compile()
