"""
Analytics Data BI — v5
Leitura inteligente via IA → Preenchimento célula a célula na planilha modelo
Rodar: streamlit run analytics_bi.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import json, os, re, io, requests, time
from io import BytesIO
from datetime import datetime
from typing import Optional, List

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

try:
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

st.set_page_config(page_title="Analytics Data BI", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def carregar_config() -> dict:
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def salvar_config(dados: dict):
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except: pass

_config = carregar_config()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#F0F4FA;}
.hdr{background:linear-gradient(135deg,#0B2545,#1B4F8A 60%,#2176FF);
     border-radius:14px;padding:22px 32px;margin-bottom:16px;
     display:flex;justify-content:space-between;align-items:center;}
.hdr h1{font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;color:white!important;margin:0;}
.hdr p{color:#B0C4E0;margin:4px 0 0;font-size:.86rem;}
.hdr .ts{color:#7096C0;font-size:.78rem;}
.sec{font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;
     color:#0B2545;border-left:4px solid #2176FF;padding-left:10px;margin:18px 0 12px;}
.card{background:white;border-radius:12px;padding:18px 22px;
      border:1px solid #D1DCF0;box-shadow:0 2px 6px rgba(11,37,69,.05);margin-bottom:12px;}
.card-label{font-size:.69rem;text-transform:uppercase;letter-spacing:.09em;color:#7096C0;font-weight:600;margin-bottom:6px;}
.kpi{font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:#0B2545;}
.kpi.g{color:#2EC4B6;}.kpi.r{color:#E63946;}.kpi.o{color:#F4A261;}
.box-ok{background:#E8FAF8;border:1px solid #2EC4B6;border-radius:10px;padding:10px 14px;color:#1A5E58;font-size:.86rem;margin:6px 0;}
.box-warn{background:#FFF4E8;border:1px solid #F4A261;border-radius:10px;padding:10px 14px;color:#7A4A1A;font-size:.86rem;margin:6px 0;}
.box-info{background:#EBF2FF;border:1px solid #2176FF;border-radius:10px;padding:10px 14px;color:#1A2B6A;font-size:.86rem;margin:6px 0;}
.box-err{background:#FFE8EA;border:1px solid #E63946;border-radius:10px;padding:10px 14px;color:#7A0010;font-size:.86rem;margin:6px 0;}
.stButton>button{background:linear-gradient(135deg,#2176FF,#1B4F8A)!important;color:white!important;
    border:none!important;border-radius:8px!important;font-weight:600!important;font-size:.87rem!important;padding:9px 18px!important;}
.stButton>button:hover{background:linear-gradient(135deg,#1B4F8A,#0B2545)!important;box-shadow:0 4px 14px rgba(33,118,255,.35)!important;}
.nav-inativo>button{background:white!important;color:#1B4F8A!important;border:1.5px solid #D1DCF0!important;
    border-radius:8px!important;font-weight:500!important;font-size:.82rem!important;}
.nav-ativo>button{background:#2176FF!important;color:white!important;border:none!important;
    border-radius:8px!important;font-weight:700!important;font-size:.82rem!important;}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid #D1DCF0;}
.stTextInput input{border-radius:8px!important;border:1px solid #D1DCF0!important;background:#F8FAFE!important;}
.stTabs [data-baseweb="tab-list"]{background:white;border-radius:10px;padding:4px;border:1px solid #D1DCF0;}
.stTabs [aria-selected="true"]{background:#2176FF!important;color:white!important;}
header[data-testid="stHeader"]{display:none;}
section[data-testid="stSidebar"]{display:none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────
MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clientes_bi")
os.makedirs(PASTA, exist_ok=True)

# ─────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────
def fmt_brl(val):
    try:
        v = float(val); s = "-" if v < 0 else ""; v = abs(v)
        if v >= 1_000_000: return f"{s}R$ {v/1_000_000:.1f} Mi"
        if v >= 1_000:     return f"{s}R$ {v/1_000:.0f} Mil"
        return f"{s}R$ {v:.0f}"
    except: return "—"

def gerar_id(nome):
    import unicodedata
    n = unicodedata.normalize("NFKD", nome.lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+","_",n).strip("_")[:40]

def path_perfil(cid):
    return os.path.join(PASTA, re.sub(r"[^a-z0-9_\-]","_",cid.lower())+".json")

def salvar(cid, dados):
    dados.setdefault("meta",{})["atualizado"] = datetime.now().isoformat()
    with open(path_perfil(cid),"w",encoding="utf-8") as f:
        json.dump(dados,f,ensure_ascii=False,indent=2)

def carregar(cid):
    p = path_perfil(cid)
    if not os.path.exists(p): return None
    with open(p,encoding="utf-8") as f: return json.load(f)

def listar():
    out = []
    for arq in os.listdir(PASTA):
        if arq.endswith(".json"):
            try:
                with open(os.path.join(PASTA,arq),encoding="utf-8") as f: d=json.load(f)
                out.append({"id":arq[:-5],"nome":d.get("nome","?"),"tipo":d.get("tipo","?"),
                             "tem_modelo":bool(d.get("modelo_path")),"at":d.get("meta",{}).get("atualizado","")[:10]})
            except: pass
    return sorted(out, key=lambda x: x["nome"].lower())

def num_mes(n): return MESES[n-1] if 1 <= n <= 12 else "jan"

# ─────────────────────────────────────────────────────────
# LEITURA DE ARQUIVOS
# ─────────────────────────────────────────────────────────
def _limpar_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = []
    contagem = {}
    for c in df.columns:
        c_str = str(c).strip()
        if c_str.lower() in ["nan","none",""]: c_str = f"col_{len(cols)}"
        if c_str in contagem:
            contagem[c_str] += 1; c_str = f"{c_str}_{contagem[c_str]}"
        else: contagem[c_str] = 0
        cols.append(c_str)
    df.columns = cols
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df[[c for c in df.columns if not c.startswith("col_")]]
    return df.reset_index(drop=True)

def ler_arquivo(b: bytes, nome: str):
    n = nome.lower()
    try:
        if n.endswith(".pdf"):
            if not PDF_OK: return None, "pdfplumber não instalado."
            dfs = []
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                for page in pdf.pages:
                    for tbl in page.extract_tables() or []:
                        if tbl and len(tbl) > 1:
                            try: dfs.append(pd.DataFrame(tbl[1:], columns=tbl[0]))
                            except: pass
            if not dfs: return None, "Nenhuma tabela no PDF."
            df = pd.concat(dfs, ignore_index=True)
            return _limpar_df(df), f"PDF: {len(df)} linhas × {df.shape[1]} colunas"
        elif n.endswith((".xlsx",".xls",".xlsm")):
            xls = pd.read_excel(io.BytesIO(b), sheet_name=None)
            dfs = [(s,df) for s,df in xls.items() if not df.dropna(how="all").empty]
            if not dfs: return None, "Excel sem dados."
            dfs.sort(key=lambda x: len(x[1]), reverse=True)
            s, df = dfs[0]
            return _limpar_df(df), f"Excel (aba '{s}'): {len(df)} linhas × {df.shape[1]} colunas"
        else:
            for enc in ["utf-8-sig","utf-8","latin1","cp1252"]:
                for sep in [";",",","\t","|"]:
                    try:
                        df = pd.read_csv(io.BytesIO(b), sep=sep, encoding=enc, on_bad_lines="skip", decimal=",")
                        if df.shape[1] >= 2: return _limpar_df(df), f"CSV: {len(df)} linhas"
                    except: pass
            return None, "Não foi possível ler o CSV."
    except Exception as e:
        return None, f"Erro: {e}"

def carregar_modelo(b: bytes, nome: str) -> pd.DataFrame:
    try:
        if nome.lower().endswith(".csv"):
            for enc in ["utf-8-sig","utf-8","latin1","cp1252"]:
                for sep in [";",",","\t"]:
                    try:
                        df = pd.read_csv(io.BytesIO(b), sep=sep, encoding=enc, decimal=",")
                        if df.shape[1] >= 5: return df
                    except: pass
        else:
            return pd.read_excel(io.BytesIO(b))
    except: pass
    return None

# ─────────────────────────────────────────────────────────
# APIS ERP
# ─────────────────────────────────────────────────────────
OMIE_BASE = "https://app.omie.com.br/api/v1"

def omie_post(ep, call, params, key, sec):
    r = requests.post(f"{OMIE_BASE}/{ep}/",
                      json={"call":call,"app_key":key,"app_secret":sec,"param":[params]},timeout=30)
    r.raise_for_status(); return r.json()

def omie_testar(key, sec):
    try:
        omie_post("geral/empresas","ListarEmpresas",{"pagina":1,"registros_por_pagina":1},key,sec)
        return True, "✅ Omie OK"
    except Exception as e: return False, f"❌ {e}"

def omie_mes(key, sec, ano, mes):
    dados = {"Ano":str(ano),"mes":num_mes(mes)}; erros = []
    try:
        m = f"{mes:02d}/{ano}"
        dre = omie_post("financas/dre","ObterRelDRE",{"dDtInicio":f"01/{m}","dDtFim":f"28/{m}"},key,sec)
        def busca(obj,k):
            if isinstance(obj,dict):
                if k in obj: return obj[k]
                for v in obj.values():
                    r=busca(v,k)
                    if r is not None: return r
            elif isinstance(obj,list):
                for i in obj:
                    r=busca(i,k)
                    if r is not None: return r
        mp = {"nReceitaBruta":"receita bruta de vendas","nCMV":"CMV (custo da mercadoria vendida)",
              "nDespesasComerciais":"despesas comerciais","nDespesasAdministrativas":"despesas administrativas",
              "nDespesasFinanceiras":"despesas financeiras líquidas","nLucroLiquido":"lucro líquido"}
        for k,c in mp.items():
            v=busca(dre,k)
            if v is not None:
                try: dados[c]=float(str(v).replace(",","."))
                except: pass
    except Exception as e: erros.append(str(e))
    return pd.DataFrame([dados]), erros

def ca_testar(tok):
    try:
        r = requests.get("https://api.contaazul.com/v1/sales",
                         headers={"Authorization":f"Bearer {tok}"},params={"page":0,"size":1},timeout=15)
        return (True,"✅ Conta Azul OK") if r.status_code==200 else (False,f"❌ {r.status_code}")
    except Exception as e: return False,f"❌ {e}"

# ─────────────────────────────────────────────────────────
# IA — LEITURA INTELIGENTE
# ─────────────────────────────────────────────────────────
def ia_ler_e_mapear(df_cliente: pd.DataFrame, df_modelo: pd.DataFrame, api_key: str) -> list:
    """
    IA analisa o arquivo do cliente e retorna lista de células para preencher na planilha modelo.
    Retorna: [{"ano": "2024", "mes": "jan", "campo": "receita bruta de vendas", "valor": 1234.56}, ...]
    """
    # Monta amostra do arquivo do cliente
    amostra_cliente = df_cliente.to_string(max_rows=80, max_cols=50)

    # Monta lista de campos da planilha modelo
    col_mes = next((c for c in df_modelo.columns if c.lower().strip() in ["mês","mes"]), None)
    col_ano = next((c for c in df_modelo.columns if c.lower().strip() in ["ano","year"]), None)
    campos_modelo = [c for c in df_modelo.columns if c not in [col_mes, col_ano, "Item"]]

    prompt = f"""Você é um especialista em contabilidade brasileira. Analise o arquivo financeiro do cliente abaixo e extraia os dados para preencher a planilha modelo.

ARQUIVO DO CLIENTE:
{amostra_cliente}

CAMPOS DISPONÍVEIS NA PLANILHA MODELO:
{json.dumps(campos_modelo, ensure_ascii=False)}

INSTRUÇÕES:
1. Identifique o ANO e o MÊS de cada dado (pode estar implícito no nome da coluna, aba ou contexto)
2. Mapeie cada valor para o campo correto da planilha modelo
3. Ignore totais, percentuais (% AV, % AH), acumulados e médias
4. Use apenas valores numéricos reais (não percentuais)
5. O mês deve ser abreviação em português: jan, fev, mar, abr, mai, jun, jul, ago, set, out, nov, dez
6. Se um valor aparecer negativo mas representa custo/despesa, converta para positivo

Retorne SOMENTE um JSON válido no formato:
{{
  "ano_detectado": "2024",
  "celulas": [
    {{"ano": "2024", "mes": "jan", "campo": "receita bruta de vendas", "valor": 1506490.26}},
    {{"ano": "2024", "mes": "jan", "campo": "CMV (custo da mercadoria vendida)", "valor": 1213936.00}},
    ...
  ]
}}"""

    sistema = "Analista financeiro especialista em contabilidade brasileira. Responda APENAS JSON válido sem markdown."
    eh_openai = not api_key.startswith("sk-ant-")

    try:
        if eh_openai and OPENAI_OK:
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o", max_tokens=8000,
                messages=[{"role":"system","content":sistema},{"role":"user","content":prompt}])
            txt = resp.choices[0].message.content.strip()
        elif ANTHROPIC_OK:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=8000,
                system=sistema,
                messages=[{"role":"user","content":prompt}])
            txt = resp.content[0].text.strip()
        else:
            return []

        txt = re.sub(r'^```json\s*','',txt); txt = re.sub(r'\s*```$','',txt)
        resultado = json.loads(txt)
        return resultado.get("celulas", [])

    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return []

def preencher_modelo(celulas: list, df_modelo: pd.DataFrame) -> pd.DataFrame:
    """
    Preenche a planilha modelo célula a célula com os dados extraídos pela IA.
    Mantém intacto tudo que não foi mapeado.
    """
    col_mes = next((c for c in df_modelo.columns if c.lower().strip() in ["mês","mes"]), None)
    col_ano = next((c for c in df_modelo.columns if c.lower().strip() in ["ano","year"]), None)

    df_resultado = df_modelo.copy()
    preenchidas = 0
    nao_encontradas = []

    for celula in celulas:
        ano  = str(celula.get("ano","")).strip()
        mes  = str(celula.get("mes","")).strip().lower()[:3]
        campo = celula.get("campo","").strip()
        valor = celula.get("valor", 0)

        if not campo or campo not in df_resultado.columns:
            nao_encontradas.append(campo)
            continue

        # Busca a linha correta por Ano + Mês
        if col_mes and col_ano:
            mask = (df_resultado[col_mes].astype(str).str.strip().str.lower().str[:3] == mes) & \
                   (df_resultado[col_ano].astype(str).str.strip() == ano)
        elif col_mes:
            mask = df_resultado[col_mes].astype(str).str.strip().str.lower().str[:3] == mes
        else:
            continue

        if not mask.any():
            nao_encontradas.append(f"{ano}/{mes}/{campo}")
            continue

        idx = df_resultado[mask].index[0]
        df_resultado.at[idx, campo] = valor
        preenchidas += 1

    return df_resultado, preenchidas, nao_encontradas

# ─────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────
for k,v in {
    "passo":1, "cid":None,
    "api_key": _config.get("anthropic_api_key",""),
    "arquivos_carregados":[], "df_consolidado":None,
    "celulas_ia":[], "df_final":None, "log":[]
}.items():
    if k not in st.session_state: st.session_state[k] = v

def ir(p): st.session_state.passo = p; st.rerun()

def log(txt, t="ok"):
    icone = {"ok":"✅","warn":"⚠️","err":"❌","info":"ℹ️"}.get(t,"•")
    st.session_state.log.insert(0, f"{datetime.now().strftime('%H:%M')} {icone} {txt}")

# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
p_at = carregar(st.session_state.cid) if st.session_state.cid else {}
st.markdown(f"""
<div class="hdr">
  <div><h1>📊 Analytics Data BI</h1>
  <p>Integração financeira · {p_at.get("nome","Nenhum cliente selecionado")}</p></div>
  <div class="ts">{datetime.now().strftime("%d/%m/%Y  %H:%M")}</div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# NAVEGAÇÃO
# ─────────────────────────────────────────────────────────
NAVS = [(1,"👥 Clientes"),(2,"➕ Novo"),(3,"🔗 Importar"),(4,"🤖 Mapear"),(5,"💾 Exportar")]
cols_nav = st.columns(5)
for col_n,(num,label) in zip(cols_nav,NAVS):
    css = "nav-ativo" if st.session_state.passo==num else "nav-inativo"
    with col_n:
        st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
        if st.button(label, key=f"nav_{num}", use_container_width=True): ir(num)
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────────────────
st.markdown('<div class="sec">🔑 API Key — Claude (sk-ant-...) ou OpenAI (sk-proj-...)</div>', unsafe_allow_html=True)
col_ak1, col_ak2, col_ak3 = st.columns([3, 1.5, 1])
with col_ak1:
    ak = st.text_input("Cole sua API Key aqui", value=st.session_state.api_key,
                       type="password", key="ak_inp", placeholder="sk-ant-... ou sk-proj-...")
    if ak and ak != st.session_state.api_key:
        st.session_state.api_key = ak
        cfg = carregar_config(); cfg["anthropic_api_key"] = ak; salvar_config(cfg)
with col_ak2:
    if st.session_state.api_key:
        tipo_ia = "🟠 OpenAI" if not st.session_state.api_key.startswith("sk-ant-") else "🔵 Anthropic"
        st.markdown(f'<div class="box-ok" style="margin-top:28px">🟢 IA ativa — {tipo_ia}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="box-warn" style="margin-top:28px">🟡 Sem chave — IA inativa</div>', unsafe_allow_html=True)
with col_ak3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.api_key:
        if st.button("🗑 Remover", key="btn_rem_key", use_container_width=True):
            st.session_state.api_key = ""
            cfg = carregar_config(); cfg.pop("anthropic_api_key",None); salvar_config(cfg); st.rerun()

st.divider()

# ═════════════════════════════════════════════════════════
# PASSO 1 — CLIENTES
# ═════════════════════════════════════════════════════════
if st.session_state.passo == 1:
    st.markdown('<div class="sec">👥 Clientes cadastrados</div>', unsafe_allow_html=True)
    clientes = listar()
    if not clientes:
        st.markdown('<div class="box-info">Nenhum cliente ainda. Clique em <b>➕ Novo</b> para começar.</div>',unsafe_allow_html=True)
    else:
        for c in clientes:
            c1,c2,c3,c4,c5,c6 = st.columns([3,1.5,1.5,1.5,1,1])
            c1.markdown(f"**{c['nome']}**")
            c2.markdown({"omie":"🟠 Omie","conta_azul":"🔵 Conta Azul","arquivo":"📄 Arquivo"}.get(c["tipo"],c["tipo"]))
            c3.markdown("✅ Modelo" if c["tem_modelo"] else "⚠️ Sem modelo")
            c4.markdown(f"🕐 {c['at']}")
            if c5.button("Abrir", key=f"ab_{c['id']}"):
                st.session_state.cid = c["id"]
                st.session_state.arquivos_carregados = []
                st.session_state.df_consolidado = None
                st.session_state.celulas_ia = []
                log(f"Cliente '{c['nome']}' selecionado"); ir(3)
            if c6.button("🗑", key=f"del_{c['id']}"):
                p = path_perfil(c["id"])
                if os.path.exists(p): os.remove(p)
                if st.session_state.cid == c["id"]: st.session_state.cid = None
                log("Cliente excluído","warn"); st.rerun()
            st.divider()

# ═════════════════════════════════════════════════════════
# PASSO 2 — NOVO CLIENTE
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 2:
    st.markdown('<div class="sec">➕ Cadastrar novo cliente</div>', unsafe_allow_html=True)
    nome = st.text_input("Nome da empresa *", placeholder="Ex: Empresa Exemplo Ltda", key="nc_nome")
    tipo = st.radio("Como os dados chegam? *",
                    ["📄 Arquivo (PDF / Excel / CSV)","🟠 Omie (API)","🔵 Conta Azul (API)"],
                    horizontal=True, key="nc_tipo")
    ak_o = as_o = tok_ca = ""
    if "Omie" in tipo:
        st.markdown('<div class="box-info">📌 Omie → Configurações → API → Criar Aplicação</div>',unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: ak_o = st.text_input("App Key", type="password", key="nc_akey")
        with c2: as_o = st.text_input("App Secret", type="password", key="nc_asec")
    elif "Conta Azul" in tipo:
        st.markdown('<div class="box-info">📌 Conta Azul → Integrações → API → Gerar Token</div>',unsafe_allow_html=True)
        tok_ca = st.text_input("Access Token", type="password", key="nc_tok")

    st.markdown("---")
    st.markdown('<div class="sec">📋 Planilha Modelo Power BI *</div>', unsafe_allow_html=True)
    st.markdown('<div class="box-info">Esta é a planilha base do Power BI. O sistema vai preenchê-la com os dados do cliente, mantendo intacto tudo que não for mapeado.</div>', unsafe_allow_html=True)
    modelo_up = st.file_uploader("Selecione a planilha modelo (CSV ou Excel)", type=["csv","xlsx","xls"], key="nc_modelo")
    if modelo_up:
        st.markdown(f'<div class="box-ok">✅ Modelo selecionado: <b>{modelo_up.name}</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ Cadastrar Cliente", use_container_width=True, key="btn_cad"):
        if not nome.strip():
            st.error("Informe o nome da empresa.")
        elif not modelo_up:
            st.error("Carregue a planilha modelo antes de cadastrar.")
        else:
            tk = "arquivo" if "Arquivo" in tipo else ("omie" if "Omie" in tipo else "conta_azul")
            cid = gerar_id(nome)
            creds = {}
            if tk == "omie": creds = {"app_key":ak_o,"app_secret":as_o}
            elif tk == "conta_azul": creds = {"access_token":tok_ca}
            # Salva planilha modelo
            ext = os.path.splitext(modelo_up.name)[1]
            modelo_path = os.path.join(PASTA, f"{cid}_modelo{ext}")
            with open(modelo_path,"wb") as f: f.write(modelo_up.read())
            salvar(cid, {"nome":nome.strip(),"tipo":tk,"credenciais":creds,
                         "modelo_path":modelo_path,"modelo_nome":modelo_up.name})
            st.session_state.cid = cid
            st.session_state.arquivos_carregados = []
            st.session_state.df_consolidado = None
            log(f"Cliente '{nome}' cadastrado")
            if tk == "omie" and ak_o:
                ok,m = omie_testar(ak_o,as_o)
                st.success(m) if ok else st.warning(m)
            elif tk == "conta_azul" and tok_ca:
                ok,m = ca_testar(tok_ca)
                st.success(m) if ok else st.warning(m)
            st.success(f"✅ **{nome}** cadastrado!")
            time.sleep(1); ir(3)

# ═════════════════════════════════════════════════════════
# PASSO 3 — IMPORTAR
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 3:
    if not st.session_state.cid:
        st.markdown('<div class="box-warn">⚠️ Cadastre ou selecione um cliente primeiro.</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid)
    tipo = perf.get("tipo","arquivo")
    creds = perf.get("credenciais",{})
    st.markdown(f'<div class="sec">🔗 Importar dados — {perf.get("nome","")}</div>',unsafe_allow_html=True)

    # Mostra status da planilha modelo
    if perf.get("modelo_path") and os.path.exists(perf["modelo_path"]):
        st.markdown(f'<div class="box-ok">📋 Planilha modelo: <b>{perf.get("modelo_nome","")}</b></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="box-warn">⚠️ Sem planilha modelo. Recadastre o cliente com a planilha modelo.</div>',unsafe_allow_html=True)

    if tipo == "arquivo":
        st.markdown("""<div class="box-info">
        📂 Adicione os arquivos do cliente <b>um por vez</b>.<br>
        Pode ser DRE, Balanço, Fluxo de Caixa — qualquer layout. A IA vai entender.
        </div>""", unsafe_allow_html=True)

        if "upload_counter" not in st.session_state: st.session_state.upload_counter = 0

        novo_arquivo = st.file_uploader("Selecione um arquivo", type=["pdf","xlsx","xls","xlsm","csv"],
                                        accept_multiple_files=False,
                                        key=f"up_single_{st.session_state.upload_counter}")

        if novo_arquivo is not None:
            nomes_ja = {a["nome"] for a in st.session_state.arquivos_carregados}
            if novo_arquivo.name not in nomes_ja:
                col_add, col_info = st.columns([1,3])
                with col_add:
                    if st.button("➕ Adicionar", use_container_width=True, key="btn_add_arq"):
                        with st.spinner(f"Lendo {novo_arquivo.name}..."):
                            df_novo, msg_r = ler_arquivo(novo_arquivo.read(), novo_arquivo.name)
                        if df_novo is not None:
                            st.session_state.arquivos_carregados.append({
                                "nome": novo_arquivo.name, "df": df_novo,
                                "linhas": len(df_novo), "colunas": df_novo.shape[1], "ok": True, "msg": msg_r})
                            log(f"'{novo_arquivo.name}' adicionado")
                        else:
                            st.session_state.arquivos_carregados.append({
                                "nome": novo_arquivo.name, "df": None,
                                "linhas": 0, "colunas": 0, "ok": False, "msg": msg_r})
                            log(f"Erro: {msg_r}","err")
                        st.session_state.upload_counter += 1; st.rerun()
                with col_info:
                    st.markdown(f'<div class="box-info">📄 <b>{novo_arquivo.name}</b> pronto para adicionar</div>',unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="box-warn">⚠️ <b>{novo_arquivo.name}</b> já está na lista.</div>',unsafe_allow_html=True)

        if st.session_state.arquivos_carregados:
            st.markdown('<div class="sec">📂 Arquivos carregados</div>', unsafe_allow_html=True)
            for i, arq in enumerate(st.session_state.arquivos_carregados):
                c1,c2,c3,c4,c5 = st.columns([3.5,1.2,1.2,1.2,0.6])
                icone = "📊" if arq["nome"].endswith((".xlsx",".xls",".xlsm")) else ("📋" if arq["nome"].endswith(".csv") else "📑")
                c1.markdown(f"{icone} **{arq['nome']}**")
                c2.markdown(f"{'✅' if arq['ok'] else '❌'} **{arq['linhas']}** linhas")
                c3.markdown(f"🔢 **{arq['colunas']}** colunas")
                c4.markdown(f'<span style="color:{"#2EC4B6" if arq["ok"] else "#E63946"};font-weight:600">{"Lido ✓" if arq["ok"] else "Erro ✗"}</span>', unsafe_allow_html=True)
                with c5:
                    if st.button("🗑", key=f"rem_{i}"):
                        st.session_state.arquivos_carregados.pop(i)
                        st.session_state.df_consolidado = None; st.rerun()
                if arq["ok"] and arq["df"] is not None:
                    key_toggle = f"show_arq_{i}"
                    if key_toggle not in st.session_state: st.session_state[key_toggle] = False
                    if st.button("🔼 Recolher" if st.session_state[key_toggle] else f"👁 Ver dados", key=f"btn_toggle_{i}"):
                        st.session_state[key_toggle] = not st.session_state[key_toggle]; st.rerun()
                    if st.session_state[key_toggle]:
                        st.dataframe(arq["df"], use_container_width=True, height=300)
                st.divider()

            dfs_ok = [a["df"] for a in st.session_state.arquivos_carregados if a["ok"] and a["df"] is not None]
            if dfs_ok:
                df_cons = pd.concat(dfs_ok, ignore_index=True) if len(dfs_ok) > 1 else dfs_ok[0]
                st.session_state.df_consolidado = df_cons
                ok_count = sum(1 for a in st.session_state.arquivos_carregados if a["ok"])
                st.markdown(f'<div class="box-ok">✅ <b>{ok_count} arquivo(s)</b> prontos para mapear</div>',unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🤖 Mapear com IA →", use_container_width=True, key="btn_ir_map"):
                if st.session_state.df_consolidado is not None:
                    st.session_state.celulas_ia = []; ir(4)
                else: st.error("Nenhum arquivo válido.")
        else:
            st.markdown('<div class="box-info">⬆️ Selecione um arquivo e clique em <b>➕ Adicionar</b>.</div>',unsafe_allow_html=True)

    elif tipo == "omie":
        st.markdown('<div class="box-info">Busque os dados diretamente do Omie.</div>',unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        with c1: ano_o = st.selectbox("Ano", list(range(2020,2031)), index=4, key="ano_om")
        with c2: mes_o = st.selectbox("Mês início", list(range(1,13)), format_func=num_mes, key="mes_om")
        with c3: mes_f = st.selectbox("Mês fim", list(range(1,13)), format_func=num_mes, index=11, key="mes_om_f")
        if st.button("🔍 Buscar do Omie", use_container_width=True, key="btn_omie"):
            k = creds.get("app_key",""); s = creds.get("app_secret","")
            dfs = []; errs = []
            pb = st.progress(0)
            rng = list(range(mes_o, mes_f+1)) if mes_f >= mes_o else [mes_o]
            with st.spinner(f"Buscando {len(rng)} mês/meses..."):
                for i,m in enumerate(rng):
                    df_m,e = omie_mes(k,s,ano_o,m); dfs.append(df_m); errs+=e
                    pb.progress((i+1)/len(rng))
            df_om = pd.concat(dfs, ignore_index=True)
            st.session_state.df_consolidado = df_om
            st.session_state.arquivos_carregados = [{"nome":f"Omie {ano_o}","df":df_om,"linhas":len(df_om),"colunas":df_om.shape[1],"ok":True,"msg":"Omie API"}]
            st.markdown(f'<div class="box-ok">✅ {len(df_om)} meses importados.</div>',unsafe_allow_html=True)
            log(f"Omie: {len(df_om)} meses")
            if errs: st.warning(" | ".join(errs[:3]))
            if st.button("🤖 Mapear com IA →", use_container_width=True, key="btn_map_om"):
                st.session_state.celulas_ia = []; ir(4)

# ═════════════════════════════════════════════════════════
# PASSO 4 — MAPEAR
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 4:
    if not st.session_state.cid:
        st.markdown('<div class="box-warn">⚠️ Selecione um cliente.</div>',unsafe_allow_html=True); st.stop()
    if st.session_state.df_consolidado is None:
        st.markdown('<div class="box-warn">⚠️ Importe os dados primeiro.</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid)
    df = st.session_state.df_consolidado
    st.markdown(f'<div class="sec">🤖 Mapeamento Inteligente — {perf.get("nome","")}</div>',unsafe_allow_html=True)

    # Carrega planilha modelo
    modelo_path = perf.get("modelo_path","")
    modelo_nome = perf.get("modelo_nome","")
    df_modelo = None
    if modelo_path and os.path.exists(modelo_path):
        with open(modelo_path,"rb") as f: modelo_bytes = f.read()
        df_modelo = carregar_modelo(modelo_bytes, modelo_nome)

    if df_modelo is None:
        st.markdown('<div class="box-err">❌ Planilha modelo não encontrada. Recadastre o cliente.</div>',unsafe_allow_html=True); st.stop()

    st.markdown(f'<div class="box-info">📋 Modelo: <b>{modelo_nome}</b> — {df_modelo.shape[0]} linhas × {df_modelo.shape[1]} colunas<br>📂 Arquivo do cliente: <b>{df.shape[0]} linhas × {df.shape[1]} colunas</b></div>',unsafe_allow_html=True)

    if not st.session_state.api_key:
        st.markdown('<div class="box-warn">⚠️ Insira a API Key acima.</div>',unsafe_allow_html=True); st.stop()

    if not st.session_state.celulas_ia:
        tipo_ia = "GPT-4o" if not st.session_state.api_key.startswith("sk-ant-") else "Claude"
        st.markdown(f'<div class="box-info">A IA ({tipo_ia}) vai analisar o arquivo do cliente e identificar exatamente quais células preencher na planilha modelo — independente do layout.</div>',unsafe_allow_html=True)

        if st.button("🤖 Analisar e Mapear com IA", use_container_width=True, key="btn_ia"):
            with st.spinner(f"🤖 {tipo_ia} analisando o arquivo... (pode levar 20-40 seg)"):
                celulas = ia_ler_e_mapear(df, df_modelo, st.session_state.api_key)
            if celulas:
                st.session_state.celulas_ia = celulas
                log(f"IA mapeou {len(celulas)} células"); st.rerun()
            else:
                st.error("IA não conseguiu extrair dados. Verifique o arquivo.")
    else:
        celulas = st.session_state.celulas_ia

        # Agrupa por ano/mês para exibir
        anos_meses = {}
        for c in celulas:
            chave = f"{c.get('ano','?')}/{c.get('mes','?')}"
            anos_meses.setdefault(chave, []).append(c)

        col_a, col_b, col_c = st.columns(3)
        col_a.markdown(f'<div class="card"><div class="card-label">Células mapeadas</div><div class="kpi">{len(celulas)}</div></div>',unsafe_allow_html=True)
        col_b.markdown(f'<div class="card"><div class="card-label">Períodos detectados</div><div class="kpi">{len(anos_meses)}</div></div>',unsafe_allow_html=True)
        col_c.markdown(f'<div class="card"><div class="card-label">Campos únicos</div><div class="kpi">{len(set(c["campo"] for c in celulas))}</div></div>',unsafe_allow_html=True)

        st.markdown('<div class="box-ok">✅ IA identificou os dados. Revise abaixo e confirme.</div>',unsafe_allow_html=True)

        # Mostra preview por período
        for periodo, itens in sorted(anos_meses.items()):
            with st.expander(f"📅 {periodo} — {len(itens)} campos"):
                for item in itens:
                    st.markdown(f"**{item['campo']}** → `{item['valor']:,.2f}`")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirmar e Exportar →", use_container_width=True, key="btn_confirmar"):
                with st.spinner("Preenchendo planilha modelo..."):
                    df_final, preenchidas, nao_enc = preencher_modelo(celulas, df_modelo)
                    st.session_state.df_final = df_final
                log(f"Preenchidas {preenchidas} células")
                if nao_enc:
                    log(f"{len(nao_enc)} campos não encontrados no modelo","warn")
                ir(5)
        with c2:
            if st.button("🔄 Refazer com IA", use_container_width=True, key="btn_refaz"):
                st.session_state.celulas_ia = []; st.rerun()

# ═════════════════════════════════════════════════════════
# PASSO 5 — EXPORTAR
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 5:
    st.markdown('<div class="sec">💾 Exportar para Power BI</div>',unsafe_allow_html=True)
    if st.session_state.df_final is None:
        st.markdown('<div class="box-warn">⚠️ Processe os dados primeiro (🤖 Mapear).</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid) if st.session_state.cid else {}
    nome_e = perf.get("nome","dados"); nid = gerar_id(nome_e)
    df_exp = st.session_state.df_final.copy()

    # Info
    col_mes = next((c for c in df_exp.columns if c.lower().strip() in ["mês","mes"]), None)
    col_ano = next((c for c in df_exp.columns if c.lower().strip() in ["ano","year"]), None)
    st.markdown(f'<div class="card"><div class="card-label">Pronto para baixar</div><b>{len(df_exp)}</b> linhas · <b>{df_exp.shape[1]}</b> colunas · formato exato da planilha modelo</div>',unsafe_allow_html=True)
    st.markdown('<div class="box-ok">✅ Planilha modelo preservada — apenas os dados do cliente foram inseridos nas células mapeadas.</div>',unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1:
        csv = df_exp.to_csv(sep=";",decimal=",",index=False,encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 CSV para Power BI", csv, file_name=f"{nid}_PowerBI.csv", mime="text/csv", use_container_width=True)
    with c2:
        buf = BytesIO()
        with pd.ExcelWriter(buf,engine="openpyxl") as w: df_exp.to_excel(w,index=False,sheet_name="Dados")
        buf.seek(0)
        st.download_button("📥 Excel", buf.getvalue(), file_name=f"{nid}_dados.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c3:
        jout = df_exp.to_json(orient="records",force_ascii=False,indent=2)
        st.download_button("📥 JSON", jout.encode(), file_name=f"{nid}_dados.json", mime="application/json", use_container_width=True)

    st.divider()
    st.markdown('<div class="sec">Preview — primeiras linhas</div>',unsafe_allow_html=True)
    cols_show = [c for c in [col_ano, col_mes, "receita bruta de vendas","lucro bruto","lucro líquido","EBITDA"] if c and c in df_exp.columns]
    if cols_show:
        st.dataframe(df_exp[cols_show], use_container_width=True, height=400)
    else:
        st.dataframe(df_exp, use_container_width=True, height=400)

    st.markdown('<div class="box-ok">✅ Substitua o CSV na pasta do Power BI e clique em Atualizar.</div>',unsafe_allow_html=True)

    if st.session_state.log:
        st.divider()
        with st.expander("📋 Log"):
            for l in st.session_state.log[:20]: st.caption(l)