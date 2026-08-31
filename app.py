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
        st.text(resultado.get("codigo_lean", ""))
        
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
    st.title("Bem vindo!")

# Opção 1: Renderização direta via st.latex (ideal para equações puras)
st.subheader("Solução Formatada (LaTeX):")
st.latex(resultado.get("solucao", ""))

# Opção 2: Renderização via Markdown (compila texto normal + equações $ ... $ ou $$ ... $$)
st.markdown(resultado.get("solucao", ""))

import streamlit as st
import subprocess
import os

st.title("Painel de Controle do Agente Gauss")

# Botão para disparar o ingestor por 24h
if st.button("🚀 Iniciar Ingestor (Rodar por 24 horas)"):
    # Comando bash que executa o script com limite de tempo de 1 dia (86400 segundos)
    # O 'nohup' e o '&' garantem que o processo rode em segundo plano sem travar o Streamlit
    comando = "nohup timeout 86400s python3 ingestor.py > ingestor.log 2>&1 &"
    
    try:
        subprocess.Popen(comando, shell=True)
        st.success("✅ Ingestor iniciado com sucesso em segundo plano! Ele será executado durante 24 horas.")
        st.info("Você pode fechar a página. O processo continuará rodando no servidor.")
    except Exception as e:
        st.error(f"❌ Erro ao iniciar o ingestor: {e}")

# Opção para visualizar os logs da execução em tempo real
if st.checkbox("📋 Mostrar logs do Ingestor"):
    if os.path.exists("ingestor.log"):
        with open("ingestor.log", "r", encoding="utf-8") as f:
            st.code(f.read()[-2000:], language="bash") # Exibe os últimos 2000 caracteres
    else:
        st.write("Nenhum log encontrado ainda.")

import time

def rodar_ingestao():
    while True:
        print("Iniciando varredura de novas questões...")
        # Lógica de raspagem e atualização do banco_provas.json aqui
        
        # Aguarda 30 minutos antes de buscar novamente
        time.sleep(1800)

if __name__ == "__main__":
    rodar_ingestao()

import streamlit as st
import subprocess
import os
import json
from langchain_core.messages import HumanMessage, SystemMessage
# Importe aqui a chamada do seu modelo / grafo (ex: llm do Groq)
from langchain_groq import ChatGroq

st.set_page_config(page_title="Agente Gauss & Ingestor", page_icon="🧮", layout="wide")

# Configuração do modelo Groq
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key)

# ------------------------------------------------------------------
# CRIAÇÃO DAS ABAS DA INTERFACE
# ------------------------------------------------------------------
aba_gauss, aba_ingestor, aba_controle = st.tabs([
    "💬 Agente Gauss (Tutor OBM/IMO)", 
    "🤖 Agente Ingestor", 
    "⚙️ Painel de Controle (24h)"
])

# ==================================================================
# ABA 1: AGENTE GAUSS (Tutor de Estatísticas e Resolução OBM/IMO)
# ==================================================================
with aba_gauss:
    st.header("Agente Gauss - Tutor OBM & IMO Shortlist")
    st.caption("Converse sobre os tópicos mais recorrentes, estratégias de prova e resoluções de alto nível.")

    # Inicializa o histórico de chat do Gauss
    if "messages_gauss" not in st.session_state:
        st.session_state.messages_gauss = []

    # Exibe mensagens anteriores
    for msg in st.session_state.messages_gauss:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input do usuário
    if prompt := st.chat_input("Pergunte sobre os assuntos mais cobrados ou peça a resolução de um problema..."):
        st.session_state.messages_gauss.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # System Prompt focado em análise de tendências OBM/IMO e resoluções
        system_gauss = SystemMessage(content="""
        Você é o Agente Gauss, um tutor e estatístico especialista em OBM (Nível 3/Universitário) e IMO Shortlists.
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
# ABA 2: AGENTE INGESTOR (Conversa sobre raspagem e inserção manual)
# ==================================================================
with aba_ingestor:
    st.header("Agente Ingestor de Dados")
    st.caption("Envie URLs do AoPS/OBM ou trechos de provas para o ingestor estruturar e salvar no banco_provas.json.")

    if "messages_ingestor" not in st.session_state:
        st.session_state.messages_ingestor = []

    for msg in st.session_state.messages_ingestor:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_ingestor := st.chat_input("Cole uma URL do AoPS ou o texto bruto de um problema para ser ingerido...", key="input_ingestor"):
        st.session_state.messages_ingestor.append({"role": "user", "content": prompt_ingestor})
        with st.chat_message("user"):
            st.markdown(prompt_ingestor)

        system_ingestor = SystemMessage(content="""
        Você é o Assistente do Agente Ingestor.
        Sua função é receber links, enunciados ou soluções brutas enviadas pelo usuário, formatá-los no padrão JSON do banco de provas da OBM/IMO e confirmar o processamento.
        Sempre retorne o código JSON formatado com tags do problema (Categoria, Tópicos, Competicao, Ano, Enunciado em LaTeX, Solucao em LaTeX).
        """)

        historia_ingestor = [system_ingestor] + [
            HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"])
            for m in st.session_state.messages_ingestor
        ]

        with st.chat_message("assistant"):
            resposta_ing = llm.invoke(historia_ingestor)
            st.markdown(resposta_ing.content)
            st.session_state.messages_ingestor.append({"role": "assistant", "content": resposta_ing.content})

# ==================================================================
# ABA 3: PAINEL DE CONTROLE DO INGESTOR AUTOMÁTICO (24 HORAS)
# ==================================================================
with aba_controle:
    st.header("Automação de Raspagem de Dados")
    st.write("Inicie o processo automático em segundo plano para varrer o AoPS e bancos de provas durante 24 horas consecutivas.")

    if st.button("🚀 Iniciar Ingestor Automático (24 Horas)"):
        comando = "nohup timeout 86400s python3 ingestor.py > ingestor.log 2>&1 &"
        try:
            subprocess.Popen(comando, shell=True)
            st.success("✅ Ingestor iniciado em segundo plano! Ele rodará por 24 horas seguidas.")
        except Exception as e:
            st.error(f"❌ Erro ao iniciar processo: {e}")

    st.subheader("Logs de Execução")
    if os.path.exists("ingestor.log"):
        with open("ingestor.log", "r", encoding="utf-8") as f:
            st.code(f.read()[-2000:], language="bash")
    else:
        st.info("Nenhum log gerado até o momento.")
