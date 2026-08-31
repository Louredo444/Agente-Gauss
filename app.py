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

REGRAS DE PROCESSAMENTO:
1. LaTeX: Inline com $...$ e Bloco com $$...$$.
2. Categorias permitidas: Algebra, Combinatoria, Geometria, Teoria dos Numeros.
3. A saída DEVE ser estritamente um bloco JSON válido no seguinte formato:

{
  "id": "COMPETICAO_ANO_NUMERO",
  "competicao": "Nome da Competição",
  "ano": 2024,
  "fase_ou_nivel": "Fase / Nível / Shortlist",
  "categoria": "Algebra",
  "topicos": ["Tópico 1"],
  "dificuldade_estimada": "Média",
  "enunciado": "Texto em LaTeX",
  "solucao": "Solução em LaTeX",
  "fonte_url": "URL ou Inserção Manual",
  "tags": ["Tag1"]
}
"""

def carregar_banco(caminho):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_banco(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

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
    caminho_banco = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_provas.json")

    aba_lean, aba_gauss, aba_lagrange, aba_banco, aba_controle = st.tabs([
        "📐 Provedor Lean 4", 
        "💬 Gauss (Tutor)", 
        "🤖 Lagrange (Ingestor)",
        "📂 Banco de Provas",
        "⚙️ Painel de Controle"
    ])

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

    # ABA 2: GAUSS
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
                system_gauss = SystemMessage(content="Você é o Gauss, tutor especialista em OBM/IMO. Use LaTeX ($e$$).")
                historia = [system_gauss] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
                    for m in st.session_state.messages_gauss
                ]
                with st.chat_message("assistant"):
                    resposta = llm.invoke(historia)
                    st.markdown(resposta.content)
                    st.session_state.messages_gauss.append({"role": "assistant", "content": resposta.content})

    # ABA 3: LAGRANGE (Ingestão com Aprovação Manual)
    with aba_lagrange:
        st.header("Lagrange - Ingestor de Dados")
        st.caption("Insira problemas para estruturação. O salvamento só ocorre após sua confirmação.")

        if "ultimo_json_processado" not in st.session_state:
            st.session_state.ultimo_json_processado = None

        if prompt_lagrange := st.chat_input("Cole o texto do problema...", key="input_chat_lagrange"):
            if not llm:
                st.error("GROQ_API_KEY não configurada.")
            else:
                with st.spinner("Estruturando problema..."):
                    system_lagrange = SystemMessage(content=SYSTEM_PROMPT_LAGRANGE)
                    resposta_lag = llm.invoke([system_lagrange, HumanMessage(content=prompt_lagrange)])
                    conteudo = resposta_lag.content.strip()

                    if conteudo.startswith("```json"):
                        conteudo = conteudo[7:]
                    if conteudo.startswith("```"):
                        conteudo = conteudo[3:]
                    if conteudo.endswith("```"):
                        conteudo = conteudo[:-3]

                    try:
                        dados_json = json.loads(conteudo.strip())
                        st.session_state.ultimo_json_processado = dados_json
                    except Exception as e:
                        st.error("Erro ao converter resposta em JSON formatado.")
                        st.text(resposta_lag.content)

        if st.session_state.ultimo_json_processado:
            item = st.session_state.ultimo_json_processado
            st.subheader("📋 Resolução Gerada para Revisão")
            st.markdown(f"**ID:** `{item.get('id')}` | **Competição:** {item.get('competicao')} ({item.get('ano')})")
            st.markdown(f"**Categoria:** `{item.get('categoria')}` | **Dificuldade:** {item.get('dificuldade_estimada')}")
            st.markdown("**Enunciado:**")
            st.markdown(item.get("enunciado", ""))
            st.markdown("**Solução:**")
            st.markdown(item.get("solucao", ""))

            col_salvar, col_descartar = st.columns([1, 1])
            with col_salvar:
                if st.button("💾 Salvar Solução no Banco", type="primary"):
                    banco = carregar_banco(caminho_banco)
                    if any(p.get("id") == item.get("id") for p in banco):
                        st.warning("Este ID já existe no banco de dados.")
                    else:
                        banco.append(item)
                        salvar_banco(caminho_banco, banco)
                        st.success("✅ Problema e solução salvos no banco com sucesso!")
                        st.session_state.ultimo_json_processado = None
                        st.rerun()

            with col_descartar:
                if st.button("❌ Descartar Resolução"):
                    st.session_state.ultimo_json_processado = None
                    st.info("Resolução descartada.")
                    st.rerun()

    # ABA 4: BANCO DE PROVAS (Com Remoção 1 a 1)
    with aba_banco:
        st.header("📂 Banco de Provas Ingeridas")
        provas = carregar_banco(caminho_banco)
        
        if provas:
            st.metric("Total de Problemas Salvos", len(provas))
            categoria_filtro = st.selectbox("Filtrar por Categoria:", ["Todas", "Algebra", "Combinatoria", "Geometria", "Teoria dos Numeros"])
            
            for idx, item in enumerate(provas):
                if categoria_filtro == "Todas" or item.get("categoria") == categoria_filtro:
                    with st.expander(f"📌 {item.get('id', 'Sem ID')} - {item.get('competicao', '')} ({item.get('ano', '')})"):
                        st.markdown(f"**Categoria:** `{item.get('categoria')}` | **Dificuldade:** {item.get('dificuldade_estimada')}")
                        st.markdown("**Enunciado:**")
                        st.markdown(item.get("enunciado", ""))
                        st.markdown("**Solução:**")
                        st.markdown(item.get("solucao", ""))
                        
                        if st.button(f"🗑️ Remover este problema", key=f"btn_remove_{idx}_{item.get('id')}"):
                            provas.pop(idx)
                            salvar_banco(caminho_banco, provas)
                            st.success(f"Problema {item.get('id')} removido com sucesso!")
                            st.rerun()
            
            st.divider()
            st.download_button(
                label="📥 Baixar banco_provas.json",
                data=json.dumps(provas, ensure_ascii=False, indent=2),
                file_name="banco_provas.json",
                mime="application/json"
            )
        else:
            st.info("Nenhum problema no banco. Utilize a aba Lagrange para aprovar e salvar novas soluções.")

    # ABA 5: PAINEL DE CONTROLE
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
