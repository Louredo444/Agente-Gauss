import os
import json
import subprocess
import streamlit as st
import pypdf
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

try:
    from agente_obm_graph import app as grafo_agente
except Exception as e:
    grafo_agente = None

st.set_page_config(page_title="Gauss & Lagrange", page_icon="🧮", layout="wide")

SYSTEM_PROMPT_LAGRANGE = """
Você é o Lagrange, o Agente de Ingestão e Estruturação de Dados Matemáticos do projeto Gauss.
Sua missão é extrair, higienizar, categorizar e formatar enunciados, soluções e metadados de problemas de olimpíadas.

FONTES: AoPS, OBM/SBM, IMO e Shortlists.

REGRAS:
1. LaTeX: Inline com $...$ e Bloco com $$...$$.
2. Categorias: Algebra, Combinatoria, Geometria, Teoria dos Numeros.
3. Saída estritamente em JSON.
"""

def checar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
        senha = st.text_input("Digite a senha de acesso:", type="password", key="input_senha_app")
        if st.button("Entrar", key="btn_login_app"):
            if senha == "1504":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if checar_senha():
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key) if groq_api_key else None

    # Estrutura com 5 Abas
    aba_lean, aba_gauss, aba_lagrange, aba_banco, aba_controle = st.tabs([
        "📐 Provedor Lean 4", 
        "💬 Gauss (Tutor)", 
        "🤖 Lagrange (Ingestor)",
        "📂 Banco de Provas",
        "⚙️ Painel de Controle"
    ])

    # Barra Lateral
    with st.sidebar:
        st.header("📚 Base de Conhecimento")
        arquivos_carregados = st.file_uploader(
            "Envie arquivos (PDF, TXT):", 
            type=["pdf", "txt"], 
            accept_multiple_files=True,
            key="uploader_materiais_sidebar"
        )
        conteudo_extra = ""
        if arquivos_carregados:
            st.success(f"{len(arquivos_carregados)} arquivo(s) carregado(s)!")
            for arq in arquivos_carregados:
                if arq.type == "text/plain":
                    conteudo_extra += arq.read().decode("utf-8") + "\n\n"
                elif arq.type == "application/pdf":
                    try:
                        leitor_pdf = pypdf.PdfReader(arq)
                        texto_pdf = ""
                        for pagina in leitor_pdf.pages:
                            t = pagina.extract_text()
                            if t:
                                texto_pdf += t + "\n"
                        conteudo_extra += f"\n--- PDF {arq.name} ---\n" + texto_pdf + "\n\n"
                    except Exception as e:
                        st.error(f"Erro no PDF {arq.name}: {e}")

    # ABA 1: PROVEDOR LEAN 4
    with aba_lean:
        st.header("🧮 Gauss - Provedor Lean 4")
        col1, col2 = st.columns([2, 1])

        with col1:
            problema = st.text_area("Enunciado do Problema:", height=150, key="txt_prob_lean")
            solucao_humana = st.text_area("Solução / Dica (Opcional):", height=100, key="txt_dica_lean")

        with col2:
            categoria = st.selectbox(
                "Categoria:", 
                ["Algebra", "Combinatoria", "Geometria", "Teoria dos Numeros"],
                key="sel_cat_lean"
            )
            max_tentativas = st.number_input("Máximo de Tentativas:", min_value=1, max_value=5, value=3, key="num_tent_lean")

        dica_com_materiais = solucao_humana
        if conteudo_extra:
            dica_com_materiais += f"\n\n[Conteúdo Extra]:\n{conteudo_extra}"

        if st.button("Executar Agente Lean", type="primary", key="btn_run_lean_exec"):
            if problema:
                if grafo_agente is None:
                    st.error("Erro: `agente_obm_graph.py` não foi carregado corretamente.")
                else:
                    estado_inicial = {
                        "problema": problema,
                        "categoria": categoria,
                        "solucao_humana": dica_com_materiais,
                        "codigo_lean": "",
                        "resultado_lean": "",
                        "sucesso": False,
                        "tentativas": 0,
                        "max_tentativas": max_tentativas,
                        "exemplos_memoria": "",
                        "solucao": ""
                    }
                    
                    with st.spinner("Processando em Lean 4..."):
                        resultado = grafo_agente.invoke(estado_inicial)
                        
                    st.subheader("Código Lean 4:")
                    st.code(resultado.get("codigo_lean", ""), language="lean")
                    
                    if resultado.get("sucesso"):
                        st.success("✅ Prova verificada com sucesso!")
                    else:
                        st.error("❌ Prova não validada no limite de tentativas.")
                        if resultado.get("resultado_lean"):
                            st.expander("Log do Lean").text(resultado["resultado_lean"])

                    if resultado.get("solucao"):
                        st.subheader("Solução Formatada (LaTeX):")
                        st.markdown(resultado.get("solucao", ""))
            else:
                st.warning("Digite o enunciado.")

    # ABA 2: GAUSS (Tutor)
    with aba_gauss:
        st.header("Gauss - Tutor OBM & IMO")
        if "messages_gauss" not in st.session_state:
            st.session_state.messages_gauss = []

        for msg in st.session_state.messages_gauss:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Digite sua dúvida...", key="input_chat_gauss"):
            st.session_state.messages_gauss.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if llm:
                system_gauss = SystemMessage(content="Você é o Gauss, tutor especialista em OBM/IMO. Use LaTeX ($ e $$).")
                historia = [system_gauss] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_gauss
                ]
                with st.chat_message("assistant"):
                    resposta = llm.invoke(historia)
                    st.markdown(resposta.content)
                    st.session_state.messages_gauss.append({"role": "assistant", "content": resposta.content})

    # ABA 3: LAGRANGE (Ingestor)
    with aba_lagrange:
        st.header("Lagrange - Ingestor de Dados")
        if "messages_lagrange" not in st.session_state:
            st.session_state.messages_lagrange = []

        for msg in st.session_state.messages_lagrange:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt_lagrange := st.chat_input("Cole o problema bruto...", key="input_chat_lagrange"):
            st.session_state.messages_lagrange.append({"role": "user", "content": prompt_lagrange})
            with st.chat_message("user"):
                st.markdown(prompt_lagrange)

            if llm:
                system_lagrange = SystemMessage(content=SYSTEM_PROMPT_LAGRANGE)
                historia_lagrange = [system_lagrange] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_lagrange
                ]
                with st.chat_message("assistant"):
                    resposta_lag = llm.invoke(historia_lagrange)
                    st.markdown(resposta_lag.content)
                    st.session_state.messages_lagrange.append({"role": "assistant", "content": resposta_lag.content})

    # ABA 4: BANCO DE PROVAS (NOVA)
    with aba_banco:
        st.header("📂 Banco de Provas Ingeridas")
        caminho_banco = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_provas.json")
        
        if os.path.exists(caminho_banco):
            with open(caminho_banco, "r", encoding="utf-8") as f:
                provas = json.load(f)
                
            st.metric("Total de Problemas", len(provas))
            categoria_filtro = st.selectbox("Filtrar por Categoria:", ["Todas", "Algebra", "Combinatoria", "Geometria", "Teoria dos Numeros"])
            
            for item in provas:
                if categoria_filtro == "Todas" or item.get("categoria") == categoria_filtro:
                    with st.expander(f"📌 {item.get('id', 'Sem ID')} - {item.get('competicao', '')} ({item.get('ano', '')})"):
                        st.markdown(f"**Categoria:** `{item.get('categoria')}` | **Dificuldade:** {item.get('dificuldade_estimada')}")
                        st.markdown("**Enunciado:**")
                        st.markdown(item.get("enunciado", ""))
                        st.markdown("**Solução:**")
                        st.markdown(item.get("solucao", ""))
                        
            st.download_button(
                label="📥 Baixar banco_provas.json",
                data=json.dumps(provas, ensure_ascii=False, indent=2),
                file_name="banco_provas.json",
                mime="application/json"
            )
        else:
            st.info("Nenhum banco de provas encontrado. Execute o Lagrange para alimentar os dados.")

    # ABA 5: PAINEL DE CONTROLE E LOGS
    with aba_controle:
        st.header("Automação de Raspagem (Lagrange)")
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_ingestor = os.path.join(diretorio_atual, "ingestor.py")

        if st.button("🚀 Iniciar Lagrange Automático (24 Horas)", key="btn_run_lagrange_24h"):
            if not os.path.exists(caminho_ingestor):
                st.error("❌ Arquivo `ingestor.py` não encontrado.")
            else:
                caminho_log = os.path.join(diretorio_atual, "ingestor.log")
                comando = f"nohup timeout 86400s python3 {caminho_ingestor} > {caminho_log} 2>&1 &"
                try:
                    subprocess.Popen(comando, shell=True)
                    st.success("✅ Lagrange iniciado em segundo plano!")
                except Exception as e:
                    st.error(f"❌ Erro ao iniciar: {e}")

        st.subheader("Logs de Execução")
        caminho_log = os.path.join(diretorio_atual, "ingestor.log")
        if os.path.exists(caminho_log):
            with open(caminho_log, "r", encoding="utf-8") as f:
                conteudo_log = f.read()
                st.code(conteudo_log[-2000:], language="bash")
                st.download_button(
                    label="📥 Baixar Log Completo",
                    data=conteudo_log,
                    file_name="ingestor.log",
                    mime="text/plain"
                )
        else:
            st.info("Nenhum log gerado até o momento.")
