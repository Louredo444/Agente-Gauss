import streamlit as st
from agente_obm_graph import app as grafo_agente

st.set_page_config(page_title="Agente Gauss - Provedor Lean 4", layout="wide")

st.title("🧮 Agente Gauss - Provedor Lean 4")

# --- BARRA LATERAL: BASE DE CONHECIMENTO E MATERIAIS ---
with st.sidebar:
    st.header("📚 Base de Conhecimento")
    st.write("Carregue livros, artigos ou materiais de estudo para alimentar o agente.")
    
    arquivos_carregados = st.file_uploader(
        "Envie arquivos (PDF, TXT):", 
        type=["pdf", "txt"], 
        accept_multiple_files=True
    )
    
    conteudo_extra = ""
    if arquivos_carregados:
        st.success(f"{len(arquivos_carregados)} arquivo(s) carregado(s)!")
        for arq in arquivos_carregados:
            st.caption(f"📖 {arq.name}")
            # Leitura simples para arquivos TXT
            if arq.type == "text/plain":
                conteudo_extra += arq.read().decode("utf-8") + "\n\n"

# --- ÁREA PRINCIPAL: ENTRADA DO PROBLEMA ---
col1, col2 = st.columns([2, 1])

with col1:
    problema = st.text_area("Enunciado do Problema:", height=150)
    solucao_humana = st.text_area("Solução / Dica Humana (Opcional):", height=100)

with col2:
    categoria = st.selectbox(
        "Categoria:", 
        ["Aritmetica", "Algebra", "Geometria", "Combinatoria"]
    )
    max_tentativas = st.number_input("Máximo de Tentativas:", min_value=1, max_value=5, value=3)

# Combine a dica humana com o conteúdo lido dos arquivos TXT
dica_com_materiais = solucao_humana
if conteudo_extra:
    dica_com_materiais += f"\n\n[Conteúdo Extra dos Materiais]:\n{conteudo_extra}"

if st.button("Executar Agente", type="primary"):
    if problema:
        estado_inicial = {
            "problema": problema,
            "categoria": categoria,
            "solucao_humana": dica_com_materiais,
            "codigo_lean": "",
            "resultado_lean": "",
            "sucesso": False,
            "tentativas": 0,
            "max_tentativas": max_tentativas,
            "exemplos_memoria": ""
        }
        
        with st.spinner("Processando e gerando prova em Lean 4..."):
            resultado = grafo_agente.invoke(estado_inicial)
            
        st.subheader("Código Lean Gerado:")
        st.code(resultado.get("codigo_lean", ""), language="lean")
        
        if resultado.get("sucesso"):
            st.success("✅ Prova validada com sucesso e salva no banco de memória!")
        else:
            st.error("❌ Não foi possível gerar uma prova válida no número de tentativas.")
            if resultado.get("resultado_lean"):
                st.expander("Ver log de erro do Lean").text(resultado["resultado_lean"])
    else:
        st.warning("Por favor, digite o enunciado do problema.")

import streamlit as st

# Sistema simples de autenticação
def checar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        senha = st.text_input("Digite a senha de acesso:", type="password")
        if st.button("Entrar"):
            if senha == "1504":  # Altere para a sua senha
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if checar_senha():
    # Todo o resto do código do app.py vem aqui dentro...
    st.title("🧮 Agente Gauss - Provedor Lean 4")
