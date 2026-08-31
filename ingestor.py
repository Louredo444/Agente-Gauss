import json
import os
import requests
from bs4 import BeautifulSoup
from groq import Groq
import time
import os

print("Iniciando a execução do Lagrange (Ingestor)...")

def rodar_ingestao():
    # Loop de execução do ingestor
    for i in range(1, 10):
        print(f"[{i}] Lagrange buscando atualizações de provas...")
        time.sleep(5)
    print("Ingestão concluída.")

if __name__ == "__main__":
    rodar_ingestao()

# Configuração da API para estruturar os dados brutos
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
CAMINHO_BANCO = "banco_provas.json"

def extrair_texto_da_web(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resposta = requests.get(url, headers=headers)
    soup = BeautifulSoup(resposta.text, "html.parser")
    # Pega o conteúdo principal da página
    return soup.get_text()

def estruturar_com_llm(texto_bruto):
    prompt = f"""
    Extraia o problema de matemática e a solução do texto abaixo.
    Retorne EXATAMENTE um objeto JSON válido no seguinte formato:
    {{
      "id": "Nome do Problema / Ano",
      "competicao": "IMO/USAMO/OBM/etc",
      "ano": 2024,
      "categoria": "Geometria/Álgebra/Teoria dos Números/Combinatória",
      "topicos": ["topico1", "topico2"],
      "enunciado": "Enunciado completo com LaTeX",
      "solucao": "Solução completa com LaTeX"
    }}

    Texto Bruto:
    {texto_bruto[:4000]}
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def salvar_no_banco(nova_questao):
    banco = []
    if os.path.exists(CAMINHO_BANCO):
        with open(CAMINHO_BANCO, "r", encoding="utf-8") as f:
            banco = json.load(f)
            
    banco.append(nova_questao)
    
    with open(CAMINHO_BANCO, "w", encoding="utf-8") as f:
        json.dump(banco, f, ensure_ascii=False, indent=2)
    print(f"✅ {nova_questao['id']} adicionado ao banco!")

# Execução
if __name__ == "__main__":
    url_alvo = input("Cole a URL do problema no AoPS/Wiki: ")
    texto = extrair_texto_da_web(url_alvo)
    questao_json = estruturar_com_llm(texto)
    salvar_no_banco(questao_json)
import subprocess

def atualizar_github():
    subprocess.run(["git", "add", "banco_provas.json"])
    subprocess.run(["git", "commit", "-m", "Auto-update: Novas questoes raspadas"])
    subprocess.run(["git", "push", "origin", "main"])

from duckduckgo_search import DDGS

SITES_ALVO = [
    "site:aops.com",
    "site:obm.org.br",
    "site:imo-official.org",
    "site:web.evanchen.cc",
    "site:https://yufeizhao.com/olympiad/"
]

def buscar_problemas_olimpiada(query):
    resultados = []
    with DDGS() as ddgs:
        for site in SITES_ALVO:
            busca_formatada = f"{query} {site}"
            response = ddgs.text(busca_formatada, max_results=3)
            if response:
                resultados.extend(response)
    return resultados

# Exemplo: buscar questões da IMO Shortlist de Geometria
# resultados = buscar_problemas_olimpiada("IMO Shortlist Geometry")


import pypdf

# Dentro da section da sidebar do app.py:
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
        
        # Leitura de arquivos TXT
        if arq.type == "text/plain":
            conteudo_extra += arq.read().decode("utf-8") + "\n\n"
            
        # Leitura de arquivos PDF
        elif arq.type == "application/pdf":
            leitor_pdf = pypdf.PdfReader(arq)
            texto_pdf = ""
            for pagina in leitor_pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_pdf += texto_pagina + "\n"
            conteudo_extra += f"\n--- Conteúdo do PDF {arq.name} ---\n" + texto_pdf + "\n\n"


SYSTEM_PROMPT_LAGRANGE = """
Você é o **Lagrange**, o Agente de Ingestão e Estruturação de Dados Matemáticos de Alto Nível do projeto Gauss.
Sua missão é extrair, higienizar, categorizar e formatar enunciados, soluções e metadados de problemas de olimpíadas de matemática (com foco principal em OBM Níveis 3/Universitário, IMO, IMO Shortlist e olimpíadas internacionais correlatas).

---

### 🌐 FONTE DE DADOS E ESCOPO DE PESQUISA
Você processa entradas originadas das seguintes fontes primárias e secundárias:
1. **Art of Problem Solving (AoPS):** Fóruns, Contests e Wiki.
2. **Olimpíada Brasileira de Matemática (OBM / SBM):** Provas oficiais e gabaritos comentados.
3. **International Mathematical Olympiad (IMO & Shortlist):** Repositório oficial e compilações em PDF.
4. **Materiais de Treinamento Olímpico:** Compilações de Evan Chen, Alexander Remorov, Yufei Zhao, entre outros.

---

### ⚙️ REGRAS DE PROCESSAMENTO E FORMATAÇÃO

1. **SINTAXE MATEMÁTICA (LaTeX Obrigatório):**
   - **Formulas Inline (no texto):** Devem usar estritamente `$ ... $`. Exemplo: $f(x + y) = f(x) + f(y)$.
   - **Formulas em Bloco (equações destacadas):** Devem usar estritamente `$$ ... $$`.
   - **Símbolos Padrão:** Preserve notações formais como $\mathbb{R}$, $\mathbb{Z}$, $\mathbb{N}$, $\pmod{p}$, $\gcd(a, b)$, $\triangle ABC$.
   - **Escapes no JSON:** Certifique-se de que a formatação do JSON utilize barras invertidas duplas (`\\`) para comandos LaTeX (ex: `\\mathbb{R}`, `\\frac{a}{b}`) para evitar erros de sintaxe ao salvar o arquivo `banco_provas.json`.

2. **CATEGORIZAÇÃO TÁTICA (Strict Categories):**
   Cada problema DEVE ser classificado em exatamente uma das quatro grandes áreas olímpicas:
   - `Algebra` (Equações Funcionais, Desigualdades, Polinômios, Sequências/Séries)
   - `Combinatoria` (Teoria dos Grafos, Invariantes, Jogos, Geometria Discreta, Contagem)
   - `Geometria` (Geometria Sintética, Geometria Analítica/Vetorial, Inversão, Cíclicos, Projetiva)
   - `Teoria dos Numeros` (Equações Diofantinas, Resíduos Quadráticos, LTE, Ordem Módular, Primos)

3. **ESTRUTURA DA SAÍDA JSON:**
   Sempre que receber um enunciado, link ou documento (PDF/TXT), sua resposta final DEVE conter um bloco de código JSON estritamente validado com a seguinte estrutura:

```json
{
  "id": "COMPETICAO_ANO_NUMERO",
  "competicao": "Nome da Competição (ex: OBM, IMO, IMO Shortlist, RMM, EGMO)",
  "ano": 2024,
  "fase_ou_nivel": "Fase 3 / Nível 3 / Shortlist",
  "categoria": "Algebra | Combinatoria | Geometria | Teoria dos Numeros",
  "topicos": ["Equações Funcionais", "Cauchys Functional Equation"],
  "dificuldade_estimada": "Fácil | Média | Difícil | Medalha de Ouro",
  "enunciado": "Texto do enunciado formatado em LaTeX...",
  "solucao": "Solução completa e detalhada formatada em LaTeX...",
  "fonte_url": "URL original se fornecida ou 'Inserção Manual/PDF'",
  "tags": ["LaTeX Validado", "Gabarito Oficial"]
}
