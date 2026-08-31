import os
import subprocess
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Importação segura para evitar SyntaxError caso agente_obm_graph esteja com falhas
try:
    from agente_obm_graph import app as grafo_agente
except Exception as e:
    grafo_agente = None

st.set_page_config(page_title="Gauss & Lagrange", page_icon="🧮", layout="wide")

# ------------------------------------------------------------------
# SISTEMA DE AUTENTICAÇÃO
# ------------------------------------------------------------------
def checar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
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
    # Inicialização do Modelo LLM Groq
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key) if groq_api_key else None

    # ------------------------------------------------------------------
    # ESTRUTURA DE ABAS PRINCIPAIS
    # ------------------------------------------------------------------
    aba_lean, aba_gauss, aba_lagrange, aba_controle = st.tabs([
        "📐 Provedor Lean 4", 
        "💬 Gauss (Tutor OBM/IMO)", 
        "🤖 Lagrange (Ingestor)", 
        "⚙️ Painel de Controle (24h)"
    ])

    # ==================================================================
    # ABA 1: PROVEDOR LEAN 4 (Geração de Provas Formais)
    # ==================================================================
    with aba_lean:
        st.header("🧮 Gauss - Provedor Lean 4")

        # BARRA LATERAL (Base de Conhecimento)
        with st.sidebar:
            st.header("📚 Base de Conhecimento")
            st.write("Carregue livros, artigos ou materiais para alimentar o agente.")
            
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
                    if arq.type == "text/plain":
                        conteudo_extra += arq.read().decode("utf-8") + "\n\n"

        # ENTRADA DO PROBLEMA
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

        dica_com_materiais = solucao_humana
        if conteudo_extra:
            dica_com_materiais += f"\n\n[Conteúdo Extra dos Materiais]:\n{conteudo_extra}"

        if st.button("Executar Agente Lean", type="primary"):
            if problema:
                if grafo_agente is None:
                    st.error("Erro: O arquivo `agente_obm_graph.py` não foi encontrado ou possui erros de importação.")
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

                    # Exibição segura da Solução Formatada em Markdown/LaTeX
                    if resultado.get("solucao"):
                        st.subheader("Solução Formatada (LaTeX):")
                        st.markdown(resultado.get("solucao", ""))
            else:
                st.warning("Por favor, digite o enunciado do problema.")

    # ==================================================================
    # ABA 2: GAUSS (Tutor OBM & IMO Shortlist)
    # ==================================================================
    with aba_gauss:
        st.header("Gauss - Tutor OBM & IMO Shortlist")
        st.caption("Converse sobre os tópicos mais recorrentes, estratégias de prova e resoluções de alto nível.")

        if "messages_gauss" not in st.session_state:
            st.session_state.messages_gauss = []

        for msg in st.session_state.messages_gauss:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Pergunte sobre os assuntos mais cobrados ou peça a resolução de um problema..."):
            st.session_state.messages_gauss.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if not llm:
                st.error("GROQ_API_KEY não configurada nas variáveis de ambiente.")
            else:
                system_gauss = SystemMessage(content="""
                Você é o Gauss, um tutor e estatístico especialista em OBM (Nível 3/Universitário) e IMO Shortlists.
                Você domina a frequência dos tópicos mais cobrados (ex: Geometria Sintética/Inversão, Equações Funcionais, LTE, Teoria dos Grafos, Invariantes).
                Ao conversar com o usuário:
                1. Responda com base nas tendências reais de provas da OBM e IMO.
                2. Use a sintaxe LaTeX ($ ... $ para inline e $$ ... $$ para bloco) para qualquer fórmula ou equação.
                3. Mantenha o tom de um treinador olímpico de nível medalha de ouro.
                """)

                historia = [system_gauss] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_gauss
                ]

                with st.chat_message("assistant"):
                    resposta = llm.invoke(historia)
                    st.markdown(resposta.content)
                    st.session_state.messages_gauss.append({"role": "assistant", "content": resposta.content})

    # ==================================================================
    # ABA 3: LAGRANGE (Assistente de Ingestão Conversacional)
    # ==================================================================
    with aba_lagrange:
        st.header("Lagrange - Ingestor de Dados")
        st.caption("Envie URLs do AoPS/OBM ou trechos de provas para o Lagrange estruturar e salvar no banco_provas.json.")

        if "messages_lagrange" not in st.session_state:
            st.session_state.messages_lagrange = []

        for msg in st.session_state.messages_lagrange:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt_lagrange := st.chat_input("Cole uma URL do AoPS ou o texto bruto de um problema para o Lagrange ingerir...", key="input_lagrange"):
            st.session_state.messages_lagrange.append({"role": "user", "content": prompt_lagrange})
            with st.chat_message("user"):
                st.markdown(prompt_lagrange)

            if not llm:
                st.error("GROQ_API_KEY não configurada nas variáveis de ambiente.")
            else:
                system_lagrange = SystemMessage(content="""
                Você é o Lagrange, o Agente Ingestor de Dados.
                Sua função é receber links, enunciados ou soluções brutas enviadas pelo usuário, formatá-los no padrão JSON do banco de provas da OBM/IMO e confirmar o processamento.
                Sempre retorne o código JSON formatado com tags do problema (Categoria, Tópicos, Competicao, Ano, Enunciado em LaTeX, Solucao em LaTeX).
                """)

                historia_lagrange = [system_lagrange] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_lagrange
                ]

                with st.chat_message("assistant"):
                    resposta_lag = llm.invoke(historia_lagrange)
                    st.markdown(resposta_lag.content)
                    st.session_state.messages_lagrange.append({"role": "assistant", "content": resposta_lag.content})

    # ==================================================================
    # ABA 4: PAINEL DE CONTROLE DO LAGRANGE (24h em Segundo Plano)
    # ==================================================================
    with aba_controle:
        st.header("Automação de Raspagem (Lagrange)")
        st.write("Inicie o processo automático em segundo plano para varrer o AoPS e bancos de provas durante 24 horas consecutivas.")

        if st.button("🚀 Iniciar Lagrange Automático (24 Horas)"):
            comando = "nohup timeout 86400s python3 ingestor.py > ingestor.log 2>&1 &"
            try:
                subprocess.Popen(comando, shell=True)
                st.success("✅ Lagrange iniciado em segundo plano! Ele rodará por 24 horas seguidas.")
            except Exception as e:
                st.error(f"❌ Erro ao iniciar processo: {e}")

        st.subheader("Logs de Execução do Lagrange")
        if os.path.exists("ingestor.log"):
            with open("ingestor.log", "r", encoding="utf-8") as f:
                st.code(f.read()[-2000:], language="bash")
        else:
            st.info("Nenhum log gerado até o momento.")

# Na Aba de Painel de Controle (app.py)
if st.button("🚀 Iniciar Lagrange Automático (24 Horas)"):
    # Obtém o caminho absoluto do diretório onde o app.py está rodando
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_ingestor = os.path.join(diretorio_atual, "ingestor.py")
    caminho_log = os.path.join(diretorio_atual, "ingestor.log")
    
    comando = f"nohup timeout 86400s python3 {caminho_ingestor} > {caminho_log} 2>&1 &"
    try:
        subprocess.Popen(comando, shell=True)
        st.success("✅ Lagrange iniciado em segundo plano! Ele rodará por 24 horas seguidas.")
    except Exception as e:
        st.error(f"❌ Erro ao iniciar processo: {e}")
