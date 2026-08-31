import os
import subprocess
import streamlit as st
import pypdf
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Importação segura do grafo Lean 4
try:
    from agente_obm_graph import app as grafo_agente
except Exception as e:
    grafo_agente = None

st.set_page_config(page_title="Gauss & Lagrange", page_icon="🧮", layout="wide")

# ------------------------------------------------------------------
# SYSTEM PROMPT DO LAGRANGE
# ------------------------------------------------------------------
SYSTEM_PROMPT_LAGRANGE = """
Você é o **Lagrange**, o Agente de Ingestão e Estruturação de Dados Matemáticos de Alto Nível do projeto Gauss.
Sua missão é extrair, higienizar, categorizar e formatar enunciados, soluções e metadados de problemas de olimpíadas de matemática (com foco principal em OBM Níveis 3/Universitário, IMO, IMO Shortlist e olimpíadas internacionais correlatas).

FONTE DE DADOS E ESCOPO DE PESQUISA:
1. Art of Problem Solving (AoPS): Fóruns, Contests e Wiki.
2. Olimpíada Brasileira de Matemática (OBM / SBM): Provas oficiais e gabaritos comentados.
3. International Mathematical Olympiad (IMO & Shortlist): Repositório oficial e compilações em PDF.
4. Materiais de Treinamento Olímpico: Compilações de Evan Chen, Alexander Remorov, Yufei Zhao, entre outros.

REGRAS DE PROCESSAMENTO E FORMATAÇÃO:
1. SINTAXE MATEMÁTICA (LaTeX Obrigatório):
   - Formulas Inline (no texto): Devem usar estritamente `$ ... $`.
   - Formulas em Bloco (equações destacadas): Devem usar estritamente `$$ ... $$`.
   - Escapes no JSON: Utilize barras invertidas duplas (`\\\\`) para comandos LaTeX (ex: `\\\\mathbb{R}`, `\\\\frac{a}{b}`).

2. CATEGORIZAÇÃO TÁTICA (Strict Categories):
   Cada problema DEVE ser classificado em exatamente uma das quatro grandes áreas:
   - `Algebra`
   - `Combinatoria`
   - `Geometria`
   - `Teoria dos Numeros`

3. ESTRUTURA DA SAÍDA JSON:
Sempre que receber um enunciado, link ou documento (PDF/TXT), sua resposta final DEVE conter um bloco JSON validado:
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
  "fonte_url": "URL original ou 'Inserção Manual/PDF'",
  "tags": ["LaTeX Validado"]
}
"""

# ------------------------------------------------------------------
# SISTEMA DE AUTENTICAÇÃO
# ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # ESTRUTURA DE ABAS
    # ------------------------------------------------------------------
    aba_lean, aba_gauss, aba_lagrange, aba_controle = st.tabs([
        "📐 Provedor Lean 4", 
        "💬 Gauss (Tutor OBM/IMO)", 
        "🤖 Lagrange (Ingestor)", 
        "⚙️ Painel de Controle (24h)"
    ])

    # BARRA LATERAL (Base de Conhecimento - Leitura de TXT e PDF)
    with st.sidebar:
        st.header("📚 Base de Conhecimento")
        st.write("Carregue livros, artigos ou materiais para alimentar os agentes.")
        
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
                st.caption(f"📖 {arq.name}")
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
                        st.error(f"Erro ao ler PDF {arq.name}: {e}")

    # ==================================================================
    # ABA 1: PROVEDOR LEAN 4
    # ==================================================================
    with aba_lean:
        st.header("🧮 Gauss - Provedor Lean 4")

        col1, col2 = st.columns([2, 1])

        with col1:
            problema = st.text_area("Enunciado do Problema:", height=150, key="txt_prob_lean")
            solucao_humana = st.text_area("Solução / Dica Humana (Opcional):", height=100, key="txt_dica_lean")

        with col2:
            categoria = st.selectbox(
                "Categoria:", 
                ["Aritmetica", "Algebra", "Geometria", "Combinatoria"],
                key="sel_cat_lean"
            )
            max_tentativas = st.number_input("Máximo de Tentativas:", min_value=1, max_value=5, value=3, key="num_tent_lean")

        dica_com_materiais = solucao_humana
        if conteudo_extra:
            dica_com_materiais += f"\n\n[Conteúdo Extra dos Materiais]:\n{conteudo_extra}"

        if st.button("Executar Agente Lean", type="primary", key="btn_run_lean_exec"):
            if problema:
                if grafo_agente is None:
                    st.error("Erro: O arquivo `agente_obm_graph.py` não está disponível ou possui erro de importação.")
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
                        st.success("✅ Prova validada com sucesso!")
                    else:
                        st.error("❌ Não foi possível gerar uma prova válida no número de tentativas.")
                        if resultado.get("resultado_lean"):
                            st.expander("Ver log de erro do Lean").text(resultado["resultado_lean"])

                    if resultado.get("solucao"):
                        st.subheader("Solução Formatada (LaTeX):")
                        st.markdown(resultado.get("solucao", ""))
            else:
                st.warning("Por favor, digite o enunciado do problema.")

    # ==================================================================
    # ABA 2: GAUSS (Tutor OBM/IMO)
    # ==================================================================
    with aba_gauss:
        st.header("Gauss - Tutor OBM & IMO Shortlist")
        st.caption("Converse sobre os tópicos mais recorrentes, estratégias de prova e resoluções de alto nível.")

        if "messages_gauss" not in st.session_state:
            st.session_state.messages_gauss = []

        for msg in st.session_state.messages_gauss:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Pergunte sobre os assuntos mais cobrados ou peça a resolução de um problema...", key="input_chat_gauss"):
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
    # ABA 3: LAGRANGE (Ingestor de Dados)
    # ==================================================================
    with aba_lagrange:
        st.header("Lagrange - Ingestor de Dados")
        st.caption("Envie URLs do AoPS/OBM ou trechos de provas para o Lagrange estruturar e salvar no banco_provas.json.")

        if "messages_lagrange" not in st.session_state:
            st.session_state.messages_lagrange = []

        for msg in st.session_state.messages_lagrange:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt_lagrange := st.chat_input("Cole uma URL do AoPS ou o texto bruto de um problema para o Lagrange ingerir...", key="input_chat_lagrange"):
            st.session_state.messages_lagrange.append({"role": "user", "content": prompt_lagrange})
            with st.chat_message("user"):
                st.markdown(prompt_lagrange)

            if not llm:
                st.error("GROQ_API_KEY não configurada nas variáveis de ambiente.")
            else:
                system_lagrange = SystemMessage(content=SYSTEM_PROMPT_LAGRANGE)

                historia_lagrange = [system_lagrange] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_lagrange
                ]

                with st.chat_message("assistant"):
                    resposta_lag = llm.invoke(historia_lagrange)
                    st.markdown(resposta_lag.content)
                    st.session_state.messages_lagrange.append({"role": "assistant", "content": resposta_lag.content})

    # ==================================================================
    # ABA 4: PAINEL DE CONTROLE (24 HORAS)
    # ==================================================================
    with aba_controle:
        st.header("Automação de Raspagem (Lagrange)")
        st.write("Inicie o processo automático em segundo plano para varrer o AoPS e bancos de provas durante 24 horas consecutivas.")

        if st.button("🚀 Iniciar Lagrange Automático (24 Horas)", key="btn_run_lagrange_24h"):
            diretorio_atual = os.path.dirname(os.path.abspath(__file__))
            caminho_ingestor = os.path.join(diretorio_atual, "ingestor.py")
            caminho_log = os.path.join(diretorio_atual, "ingestor.log")
            
            comando = f"nohup timeout 86400s python3 {caminho_ingestor} > {caminho_log} 2>&1 &"
            try:
                subprocess.Popen(comando, shell=True)
                st.success("✅ Lagrange iniciado em segundo plano! Ele rodará por 24 horas seguidas.")
            except Exception as e:
                st.error(f"❌ Erro ao iniciar processo: {e}")

        st.subheader("Logs de Execução do Lagrange")
        caminho_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ingestor.log")
        if os.path.exists(caminho_log):
            with open(caminho_log, "r", encoding="utf-8") as f:
                st.code(f.read()[-2000:], language="bash")
        elif os.path.exists("ingestor.log"):
            with open("ingestor.log", "r", encoding="utf-8") as f:
                st.code(f.read()[-2000:], language="bash")
        else:
            st.info("Nenhum log gerado até o momento.")
