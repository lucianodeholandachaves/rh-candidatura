"""
Analytics Data BI — Sistema Completo v4
Importação múltipla → Mapeamento IA → Cálculo → Exportação Power BI
Rodar: streamlit run analytics_bi.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import json, os, re, io, requests, time
from io import BytesIO
from datetime import datetime
from typing import Optional, Tuple, List

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

try:
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

st.set_page_config(page_title="Analytics Data BI", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#F0F4FA;}

.hdr{background:linear-gradient(135deg,#0B2545,#1B4F8A 60%,#2176FF);
     border-radius:14px;padding:22px 32px;margin-bottom:16px;
     display:flex;justify-content:space-between;align-items:center;}
.hdr h1{font-family:'Space Grotesk',sans-serif;font-size:1.6rem;
        font-weight:700;color:white!important;margin:0;}
.hdr p{color:#B0C4E0;margin:4px 0 0;font-size:.86rem;}
.hdr .ts{color:#7096C0;font-size:.78rem;}

.sec{font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;
     color:#0B2545;border-left:4px solid #2176FF;padding-left:10px;margin:18px 0 12px;}
.card{background:white;border-radius:12px;padding:18px 22px;
      border:1px solid #D1DCF0;box-shadow:0 2px 6px rgba(11,37,69,.05);margin-bottom:12px;}
.card-label{font-size:.69rem;text-transform:uppercase;letter-spacing:.09em;
            color:#7096C0;font-weight:600;margin-bottom:6px;}
.kpi{font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:#0B2545;}
.kpi.g{color:#2EC4B6;}.kpi.r{color:#E63946;}.kpi.o{color:#F4A261;}

.box-ok{background:#E8FAF8;border:1px solid #2EC4B6;border-radius:10px;
        padding:10px 14px;color:#1A5E58;font-size:.86rem;margin:6px 0;}
.box-warn{background:#FFF4E8;border:1px solid #F4A261;border-radius:10px;
          padding:10px 14px;color:#7A4A1A;font-size:.86rem;margin:6px 0;}
.box-info{background:#EBF2FF;border:1px solid #2176FF;border-radius:10px;
          padding:10px 14px;color:#1A2B6A;font-size:.86rem;margin:6px 0;}
.box-err{background:#FFE8EA;border:1px solid #E63946;border-radius:10px;
         padding:10px 14px;color:#7A0010;font-size:.86rem;margin:6px 0;}

.b-ok{background:#E8FAF8;color:#1A6058;border:1px solid #2EC4B6;
      border-radius:20px;padding:1px 9px;font-size:.73rem;font-weight:600;}
.b-warn{background:#FFF4E8;color:#7A4A1A;border:1px solid #F4A261;
        border-radius:20px;padding:1px 9px;font-size:.73rem;font-weight:600;}
.b-err{background:#FFE8EA;color:#7A0010;border:1px solid #E63946;
       border-radius:20px;padding:1px 9px;font-size:.73rem;font-weight:600;}

/* ARQUIVO CARD */
.arq-card{background:white;border-radius:10px;padding:12px 16px;
          border:1px solid #D1DCF0;margin-bottom:8px;
          display:flex;align-items:center;justify-content:space-between;}
.arq-nome{font-weight:600;font-size:.88rem;color:#0B2545;}
.arq-info{font-size:.76rem;color:#7096C0;margin-top:2px;}
.arq-status-ok{color:#2EC4B6;font-size:.8rem;font-weight:600;}
.arq-status-err{color:#E63946;font-size:.8rem;font-weight:600;}

.stButton>button{
    background:linear-gradient(135deg,#2176FF,#1B4F8A)!important;
    color:white!important;border:none!important;border-radius:8px!important;
    font-weight:600!important;font-size:.87rem!important;padding:9px 18px!important;}
.stButton>button:hover{
    background:linear-gradient(135deg,#1B4F8A,#0B2545)!important;
    box-shadow:0 4px 14px rgba(33,118,255,.35)!important;}

.nav-inativo>button{background:white!important;color:#1B4F8A!important;
    border:1.5px solid #D1DCF0!important;border-radius:8px!important;
    font-weight:500!important;font-size:.82rem!important;}
.nav-ativo>button{background:#2176FF!important;color:white!important;
    border:none!important;border-radius:8px!important;
    font-weight:700!important;font-size:.82rem!important;}

[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid #D1DCF0;}
.stTextInput input,.stNumberInput input{border-radius:8px!important;border:1px solid #D1DCF0!important;background:#F8FAFE!important;}
.stTabs [data-baseweb="tab-list"]{background:white;border-radius:10px;padding:4px;border:1px solid #D1DCF0;}
.stTabs [aria-selected="true"]{background:#2176FF!important;color:white!important;}
header[data-testid="stHeader"]{display:none;}
section[data-testid="stSidebar"]{display:none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# CAMPOS CANÔNICOS
# ─────────────────────────────────────────────────────────
CAMPOS = {
    "receita bruta de vendas":       {"g":"Receita",    "sin":["faturamento bruto","receita operacional","vendas brutas","faturamento","total receitas"]},
    "impostos sobre vendas":         {"g":"Receita",    "sin":["impostos","icms","pis cofins","(-) impostos","tributos vendas","simples nacional"]},
    "devoluções de vendas":          {"g":"Receita",    "sin":["devolucoes","abatimentos","(-) devolucoes","cancelamentos","estornos vendas"]},
    "CMV (custo da mercadoria vendida)": {"g":"Custo",  "sin":["cmv","custo mercadoria","custo das mercadorias","cpv","custo produtos vendidos","cogs"]},
    "estoque inicial do mês de mercadorias para revenda saldo": {"g":"Custo","sin":["estoque inicial","saldo inicial estoque","inventario inicial"]},
    "estoque final do mês de mercadorias para revenda saldo":   {"g":"Custo","sin":["estoque final","saldo final estoque","inventario final","estoque","valor estoque"]},
    "despesas comerciais":           {"g":"Despesas",   "sin":["despesas comerciais","desp vendas","marketing","publicidade","comercial"]},
    "despesas administrativas":      {"g":"Despesas",   "sin":["despesas administrativas","desp adm","dga","administrativo","custos fixos","folha pagamento","pessoal","rh","salarios"]},
    "despesas financeiras líquidas": {"g":"Despesas",   "sin":["despesas financeiras","juros","encargos financeiros","tarifas bancarias","iof"]},
    "despesas com depreciações e amortizações": {"g":"Despesas","sin":["depreciacao","amortizacao","d&a"]},
    "receitas não operacionais":     {"g":"N.Operac.",  "sin":["receitas nao operacionais","outras receitas","receitas financeiras","receitas diversas"]},
    "despesas não operacionais":     {"g":"N.Operac.",  "sin":["despesas nao operacionais","outras despesas","perdas","despesas diversas"]},
    "provisão para imposto de renda":{"g":"N.Operac.",  "sin":["ir","irpj","imposto de renda","provisao ir"]},
    "provisão para contribuição social":{"g":"N.Operac.","sin":["csll","contribuicao social","provisao csll"]},
    "disponibilidades saldo":        {"g":"Ativo",      "sin":["caixa","disponibilidades","caixa e equivalentes","banco","saldo caixa","disponivel"]},
    "contas a receber saldo":        {"g":"Ativo",      "sin":["contas a receber","duplicatas a receber","creditos clientes","ar","clientes","recebiveis"]},
    "Outros AC":                     {"g":"Ativo",      "sin":["outros ativos circulantes","outros ac","outros creditos","adiantamentos"]},
    "Ativo NC":                      {"g":"Ativo",      "sin":["ativo nao circulante","ativo fixo","imobilizado","ativo permanente"]},
    "contas a pagar de fornecedores saldo":{"g":"Passivo","sin":["contas a pagar","fornecedores","duplicatas a pagar","titulos a pagar"]},
    "Passivos Financeiros":          {"g":"Passivo",    "sin":["emprestimos","financiamentos","dividas","passivos financeiros","divida financeira"]},
    "Outros PC":                     {"g":"Passivo",    "sin":["outros passivos circulantes","outros pc","obrigacoes tributarias","salarios a pagar"]},
    "Passivo NC":                    {"g":"Passivo",    "sin":["passivo nao circulante","dividas longo prazo","exigivel lp","financiamentos lp"]},
    "Disponibilidades entradas":     {"g":"Fluxo",      "sin":["entradas caixa","recebimentos totais","total entradas","entradas","caixa entradas"]},
    "Disponibilidades Saida":        {"g":"Fluxo",      "sin":["saidas caixa","pagamentos totais","total saidas","saidas","caixa saidas","desembolsos"]},
    "Centro de Custos Entradas 1":   {"g":"Fluxo",      "sin":["mastercard","bandeira 1","canal 1","entradas 1"]},
    "Centro de Custos Entradas 2":   {"g":"Fluxo",      "sin":["visa","bandeira 2","canal 2","entradas 2"]},
    "Centro de Custos Entradas 3":   {"g":"Fluxo",      "sin":["elo","bandeira 3","canal 3","entradas 3"]},
    "Centro de Custos Entradas 4":   {"g":"Fluxo",      "sin":["amex","american express","bandeira 4","entradas 4"]},
    "Centro de Custos Saidas 1":     {"g":"Fluxo",      "sin":["saidas 1","cc saidas 1","saida 1"]},
    "Centro de Custos Saidas 2":     {"g":"Fluxo",      "sin":["saidas 2","cc saidas 2","saida 2"]},
    "Centro de Custos Saidas 3":     {"g":"Fluxo",      "sin":["saidas 3","cc saidas 3","saida 3"]},
    "Centro de Custos Saidas 4":     {"g":"Fluxo",      "sin":["saidas 4","cc saidas 4","saida 4"]},
    "numero de vendas":              {"g":"Outros",     "sin":["quantidade vendas","qtd vendas","pedidos","transacoes","total pedidos"]},
    "pró-labore/distribuição de lucro":{"g":"Outros",  "sin":["pro labore","prolabore","distribuicao lucros","retiradas socios"]},
    "Aporte":                        {"g":"Outros",     "sin":["aporte capital","investimento socios","aumento capital","aportes"]},
    "INADIMP 30 OFF":                {"g":"Outros",     "sin":["inadimplencia","devedores duvidosos","pdd","titulos vencidos"]},
    "OBSOL 90 OFF":                  {"g":"Outros",     "sin":["obsolescencia estoque","estoque obsoleto","estoque parado"]},
}
LISTA_CAMPOS = list(CAMPOS.keys())
MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clientes_bi")
os.makedirs(PASTA, exist_ok=True)

# ─────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────
def safe_div(a, b):
    return np.where(b != 0, a / b, 0.0)

def fmt_brl(val):
    try:
        v = float(val); s = "-" if v < 0 else ""; v = abs(v)
        if v >= 1_000_000: return f"{s}R$ {v/1_000_000:.1f} Mi"
        if v >= 1_000:     return f"{s}R$ {v/1_000:.0f} Mil"
        return f"{s}R$ {v:.0f}"
    except: return "—"

def num_mes(n): return MESES[n-1] if 1 <= n <= 12 else "jan"

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
                             "mapeado":bool(d.get("mapeamento")),"at":d.get("meta",{}).get("atualizado","")[:10]})
            except: pass
    return sorted(out, key=lambda x: x["nome"].lower())

# ─────────────────────────────────────────────────────────
# LEITURA DE ARQUIVOS
# ─────────────────────────────────────────────────────────
def ler_arquivo(b: bytes, nome: str) -> Tuple[Optional[pd.DataFrame], str]:
    n = nome.lower()
    if   n.endswith(".pdf"):                    return _pdf(b)
    elif n.endswith((".xlsx",".xls",".xlsm")):  return _excel(b)
    else:                                        return _csv(b)

def _pdf(b):
    if not PDF_OK: return None, "pdfplumber não instalado."
    dfs = []
    try:
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            for page in pdf.pages:
                for tbl in page.extract_tables() or []:
                    if tbl and len(tbl) > 1:
                        try: dfs.append(pd.DataFrame(tbl[1:], columns=tbl[0]))
                        except: pass
                if not page.extract_tables():
                    txt = page.extract_text() or ""
                    rows = [re.split(r'\s{2,}|\t', l.strip()) for l in txt.splitlines() if len(l.strip()) > 5]
                    if rows:
                        mc = max(len(r) for r in rows)
                        dfs.append(pd.DataFrame([r+[""]*(mc-len(r)) for r in rows]))
        if not dfs: return None, "Nenhuma tabela no PDF."
        df = pd.concat(dfs, ignore_index=True).dropna(how="all").dropna(axis=1,how="all")
        return df, f"PDF: {len(df)} linhas × {df.shape[1]} colunas"
    except Exception as e: return None, f"Erro PDF: {e}"

def _excel(b):
    try:
        xls = pd.read_excel(io.BytesIO(b), sheet_name=None)
        dfs = [(s, df.dropna(how="all").dropna(axis=1,how="all"))
               for s,df in xls.items() if not df.dropna(how="all").empty]
        if not dfs: return None, "Excel sem dados."
        dfs.sort(key=lambda x: len(x[1]), reverse=True)
        s, df = dfs[0]
        return df, f"Excel (aba '{s}'): {len(df)} linhas × {df.shape[1]} colunas"
    except Exception as e: return None, f"Erro Excel: {e}"

def _csv(b):
    for enc in ["utf-8-sig","utf-8","latin1","cp1252"]:
        for sep in [";",",","\t","|"]:
            try:
                df = pd.read_csv(io.BytesIO(b), sep=sep, encoding=enc,
                                  on_bad_lines="skip", decimal=",")
                if df.shape[1] >= 2:
                    return df.dropna(how="all").dropna(axis=1,how="all"), f"CSV: {len(df)} linhas"
            except: pass
    return None, "Não foi possível ler o CSV."

def consolidar_arquivos(lista_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Consolida múltiplos DataFrames num único.
    Se tiverem colunas em comum, une lado a lado (merge por index).
    Se não tiverem, concatena as colunas.
    """
    if not lista_dfs: return pd.DataFrame()
    if len(lista_dfs) == 1: return lista_dfs[0]

    # Detecta colunas de período em cada df
    def get_periodo_col(df, nomes):
        return next((c for c in df.columns if c.lower().strip() in nomes), None)

    # Tenta alinhar por Ano+Mês se existirem
    dfs_com_periodo = []
    dfs_sem_periodo = []
    for df in lista_dfs:
        mc = get_periodo_col(df, ["mês","mes","month"])
        ac = get_periodo_col(df, ["ano","year"])
        if mc and ac:
            dfs_com_periodo.append((df, ac, mc))
        else:
            dfs_sem_periodo.append(df)

    if len(dfs_com_periodo) >= 2:
        # Merge por Ano + Mês
        base_df, base_ac, base_mc = dfs_com_periodo[0]
        base_df = base_df.rename(columns={base_ac:"Ano", base_mc:"mês"})
        for df, ac, mc in dfs_com_periodo[1:]:
            df = df.rename(columns={ac:"Ano", mc:"mês"})
            cols_novas = [c for c in df.columns if c not in base_df.columns or c in ["Ano","mês"]]
            base_df = pd.merge(base_df, df[cols_novas], on=["Ano","mês"], how="outer")
        # Adiciona dfs sem período coluna a coluna
        for df in dfs_sem_periodo:
            for c in df.columns:
                if c not in base_df.columns:
                    base_df[c] = df[c].values[:len(base_df)] if len(df) >= len(base_df) else pd.Series(dtype=float)
        return base_df
    else:
        # Concatena colunas lado a lado
        resultado = pd.concat(lista_dfs, axis=1)
        resultado = resultado.loc[:,~resultado.columns.duplicated()]
        return resultado

# ─────────────────────────────────────────────────────────
# APIS
# ─────────────────────────────────────────────────────────
OMIE_BASE = "https://app.omie.com.br/api/v1"

def omie_post(ep, call, params, key, sec):
    r = requests.post(f"{OMIE_BASE}/{ep}/",
                      json={"call":call,"app_key":key,"app_secret":sec,"param":[params]},
                      timeout=30)
    r.raise_for_status(); return r.json()

def omie_testar(key, sec):
    try:
        omie_post("geral/empresas","ListarEmpresas",{"pagina":1,"registros_por_pagina":1},key,sec)
        return True, "✅ Conexão Omie OK"
    except Exception as e: return False, f"❌ {e}"

def omie_mes(key, sec, ano, mes):
    dados = {"Ano":ano,"mês":num_mes(mes)}; erros = []
    try:
        m = f"{mes:02d}/{ano}"
        dre = omie_post("financas/dre","ObterRelDRE",
                        {"dDtInicio":f"01/{m}","dDtFim":f"28/{m}"},key,sec)
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
        mp = {"nReceitaBruta":"receita bruta de vendas",
              "nCMV":"CMV (custo da mercadoria vendida)",
              "nDespesasComerciais":"despesas comerciais",
              "nDespesasAdministrativas":"despesas administrativas",
              "nDespesasFinanceiras":"despesas financeiras líquidas",
              "nLucroLiquido":"lucro líquido"}
        for k,c in mp.items():
            v=busca(dre,k)
            if v is not None:
                try: dados[c]=float(str(v).replace(",","."))
                except: pass
    except Exception as e: erros.append(str(e))
    try:
        cr = omie_post("financas/contareceber","ListarContasReceber",
                       {"pagina":1,"registros_por_pagina":500,
                        "filtrar_por_data_de":f"01/{mes:02d}/{ano}",
                        "filtrar_por_data_ate":f"28/{mes:02d}/{ano}"},key,sec)
        dados["contas a receber saldo"] = sum(
            float(str(i.get("nValorTitulo",0)).replace(",","."))
            for i in cr.get("conta_receber_cadastro",[]) if isinstance(i,dict))
    except Exception as e: erros.append(str(e))
    try:
        cp = omie_post("financas/contapagar","ListarContasPagar",
                       {"pagina":1,"registros_por_pagina":500,
                        "filtrar_por_data_de":f"01/{mes:02d}/{ano}",
                        "filtrar_por_data_ate":f"28/{mes:02d}/{ano}"},key,sec)
        dados["contas a pagar de fornecedores saldo"] = sum(
            float(str(i.get("nValorTitulo",0)).replace(",","."))
            for i in cp.get("conta_pagar_cadastro",[]) if isinstance(i,dict))
    except Exception as e: erros.append(str(e))
    return pd.DataFrame([dados]), erros

def ca_testar(tok):
    try:
        r = requests.get("https://api.contaazul.com/v1/sales",
                         headers={"Authorization":f"Bearer {tok}"},
                         params={"page":0,"size":1},timeout=15)
        return (True,"✅ Conta Azul OK") if r.status_code==200 else (False,f"❌ Status {r.status_code}")
    except Exception as e: return False,f"❌ {e}"

def ca_mes(tok, ano, mes):
    h = {"Authorization":f"Bearer {tok}"}
    ini = f"{ano}-{mes:02d}-01"; fim = f"{ano}-{mes:02d}-28"
    dados = {"Ano":ano,"mês":num_mes(mes)}
    try:
        r = requests.get("https://api.contaazul.com/v1/sales",headers=h,
                         params={"emission_start":ini,"emission_end":fim,"size":500},timeout=20)
        if r.status_code==200:
            dados["receita bruta de vendas"] = sum(
                float(v.get("total",0)) for v in r.json() if isinstance(v,dict))
    except: pass
    try:
        r = requests.get("https://api.contaazul.com/v1/financial-movements",headers=h,
                         params={"start_date":ini,"end_date":fim,"size":500},timeout=20)
        if r.status_code==200:
            movs = r.json()
            if isinstance(movs,list):
                dados["Disponibilidades entradas"] = sum(float(m.get("value",0)) for m in movs if isinstance(m,dict) and m.get("type")=="INCOME")
                dados["Disponibilidades Saida"]    = sum(float(m.get("value",0)) for m in movs if isinstance(m,dict) and m.get("type")=="EXPENSE")
    except: pass
    return pd.DataFrame([dados])

# ─────────────────────────────────────────────────────────
# MAPEAMENTO COM IA
# ─────────────────────────────────────────────────────────
def mapear_ia(df: pd.DataFrame, api_key: str) -> dict:
    if not ANTHROPIC_OK: return {"erro":"anthropic não instalado","mapeamento":{}}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        colunas = "\n".join(
            f'- "{c}": {df[c].dropna().head(3).tolist()}' for c in df.columns)
        campos = "\n".join(
            f'- "{c}" ({info["g"]}): ex: {", ".join(info["sin"][:3])}'
            for c,info in CAMPOS.items())
        prompt = f"""Colunas do cliente com amostras de valores:
{colunas}

Campos do modelo de destino:
{campos}

Mapeie cada coluna do cliente para o campo canônico correto (ou null se não existir).
Responda SOMENTE com JSON válido:
{{"mapeamento":{{"COLUNA":{{"campo":"campo_canonico_ou_null","confianca":0-100,"motivo":"1 linha"}}}}}}"""
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096,
            system="Especialista contabilidade brasileira. Responda APENAS JSON válido.",
            messages=[{"role":"user","content":prompt}])
        txt = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', txt, re.DOTALL)
        return json.loads(m.group() if m else txt)
    except Exception as e: return {"erro":str(e),"mapeamento":{}}

# ─────────────────────────────────────────────────────────
# MOTOR DE CÁLCULO
# ─────────────────────────────────────────────────────────
def calcular(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    def col(c):
        if c in d.columns: return pd.to_numeric(d[c],errors="coerce").fillna(0.)
        return pd.Series(0., index=d.index)

    d["deduções da receita bruta"]  = col("impostos sobre vendas")+col("devoluções de vendas")
    d["receita líquida de vendas"]  = col("receita bruta de vendas")-d["deduções da receita bruta"]
    d["lucro bruto"]                = d["receita líquida de vendas"]-col("CMV (custo da mercadoria vendida)")
    d["despesas operacionais totais"] = (col("despesas comerciais")+col("despesas administrativas")+
        col("despesas financeiras líquidas")+col("despesas com depreciações e amortizações"))
    d["lucro operacional"]          = d["lucro bruto"]-d["despesas operacionais totais"]
    d["resultado antes da provisão para imposto de renda e contribuição social"] = (
        d["lucro operacional"]+col("receitas não operacionais")-col("despesas não operacionais"))
    d["lucro líquido"]              = (d["resultado antes da provisão para imposto de renda e contribuição social"]
        -col("provisão para imposto de renda")-col("provisão para contribuição social"))
    d["ativo circulante saldo"]     = (col("disponibilidades saldo")+col("contas a receber saldo")+
        col("estoque final do mês de mercadorias para revenda saldo")+col("Outros AC"))
    d["passivo circulante saldo"]   = col("contas a pagar de fornecedores saldo")+col("Passivos Financeiros")+col("Outros PC")
    d["ativo total saldo"]          = d["ativo circulante saldo"]+col("Ativo NC")
    d["passivo total saldo"]        = d["passivo circulante saldo"]+col("Passivo NC")
    d["patrimônio líquido"]         = d["ativo total saldo"]-d["passivo total saldo"]
    d["Lucratividade"]              = safe_div(d["lucro líquido"],d["receita líquida de vendas"])
    d["Margem de Contribuição"]     = safe_div(d["lucro bruto"],d["receita líquida de vendas"])
    cp = col("contas a pagar de fornecedores saldo"); cpm=(cp+cp.shift(1).fillna(cp))/2
    compras = (col("estoque final do mês de mercadorias para revenda saldo")+
               col("CMV (custo da mercadoria vendida)")-
               col("estoque inicial do mês de mercadorias para revenda saldo"))*12
    d["Prazo médio de pagamentos"]  = safe_div(cpm,compras)*365
    cr = col("contas a receber saldo"); crm=(cr+cr.shift(1).fillna(cr))/2
    d["Prazo médio de recebimentos"] = safe_div(crm,d["receita líquida de vendas"]*12)*365
    em = (col("estoque inicial do mês de mercadorias para revenda saldo")+
          col("estoque final do mês de mercadorias para revenda saldo"))/2
    d["giro do estoque"]            = safe_div(col("CMV (custo da mercadoria vendida)"),em)
    d["Prazo médio de estocagem"]   = safe_div(30,d["giro do estoque"])
    d["ciclo de caixa"]             = d["Prazo médio de recebimentos"]+d["Prazo médio de estocagem"]-d["Prazo médio de pagamentos"]
    d["liquidez imediata"]          = safe_div(col("disponibilidades saldo"),d["passivo circulante saldo"])
    d["roe"]                        = safe_div(d["lucro líquido"],d["patrimônio líquido"])
    ebitda = (d["lucro líquido"]+col("provisão para imposto de renda")+col("provisão para contribuição social")+
              col("despesas financeiras líquidas")+col("despesas com depreciações e amortizações"))
    d["EBITDA"]                     = safe_div(ebitda,d["receita líquida de vendas"])
    d["Margem Ebitda"]              = d["EBITDA"]
    d["ticket medio"]               = safe_div(d["receita líquida de vendas"],col("numero de vendas"))
    d["ICD"]                        = safe_div(ebitda,col("Passivos Financeiros")-col("disponibilidades saldo"))
    d["termômetro de kanitz"]       = (
        safe_div(d["lucro líquido"],d["patrimônio líquido"])*0.05+
        safe_div(d["ativo total saldo"],d["passivo total saldo"])*1.65+
        safe_div(d["ativo circulante saldo"]-col("estoque final do mês de mercadorias para revenda saldo"),
                 d["passivo circulante saldo"])*3.55+
        safe_div(d["ativo circulante saldo"],d["passivo circulante saldo"])*1.06+
        safe_div(d["passivo total saldo"],d["patrimônio líquido"])*0.33)
    if "mês" in d.columns and "Ano" in d.columns:
        mm = {m:str(i+1).zfill(2) for i,m in enumerate(MESES)}
        mn = d["mês"].astype(str).str.strip().str.lower().str[:3].map(mm)
        d["Data"] = pd.to_datetime(d["Ano"].astype(str)+"-"+mn.fillna("01")+"-01",errors="coerce")
    return d

def aplicar_mapa(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    col_mes = next((c for c in df.columns if c.lower().strip() in ["mês","mes","month"]), None)
    col_ano = next((c for c in df.columns if c.lower().strip() in ["ano","year"]), None)
    res = {}
    for col_c, campo in mapa.items():
        if campo and col_c in df.columns:
            v = pd.to_numeric(df[col_c], errors="coerce").fillna(0)
            res[campo] = res.get(campo, pd.Series(0., index=df.index)) + v
    df_out = pd.DataFrame(res, index=df.index)
    if col_mes and "mês" not in df_out.columns: df_out["mês"] = df[col_mes].values
    if col_ano and "Ano" not in df_out.columns: df_out["Ano"] = df[col_ano].values
    for c in LISTA_CAMPOS:
        if c not in df_out.columns: df_out[c] = 0.
    return df_out

# ─────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────
for k,v in {
    "passo":1, "cid":None, "api_key":"",
    "arquivos_carregados":[],   # lista de {"nome","df","linhas","colunas","ok"}
    "df_consolidado":None,      # df consolidado de todos os arquivos
    "sug_ia":None, "mapa":{},
    "df_final":None, "log":[]
}.items():
    if k not in st.session_state: st.session_state[k] = v

def ir(p):
    st.session_state.passo = p
    st.rerun()

def log(txt, t="ok"):
    icone = {"ok":"✅","warn":"⚠️","err":"❌","info":"ℹ️"}.get(t,"•")
    st.session_state.log.insert(0, f"{datetime.now().strftime('%H:%M')} {icone} {txt}")

# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
p_at = carregar(st.session_state.cid) if st.session_state.cid else {}
st.markdown(f"""
<div class="hdr">
  <div>
    <h1>📊 Analytics Data BI</h1>
    <p>Integração financeira · {p_at.get("nome","Nenhum cliente selecionado")}</p>
  </div>
  <div class="ts">{datetime.now().strftime("%d/%m/%Y  %H:%M")}</div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# NAVEGAÇÃO — 6 BOTÕES REAIS
# ─────────────────────────────────────────────────────────
NAVS = [(1,"👥 Clientes"),(2,"➕ Novo"),(3,"🔗 Importar"),
        (4,"🤖 Mapear"),(5,"⚙️ Processar"),(6,"💾 Exportar")]

cols_nav = st.columns(6)
for col_n,(num,label) in zip(cols_nav,NAVS):
    css = "nav-ativo" if st.session_state.passo==num else "nav-inativo"
    with col_n:
        st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
        if st.button(label, key=f"nav_{num}", use_container_width=True): ir(num)
        st.markdown('</div>', unsafe_allow_html=True)

# API KEY — expander sempre visível
with st.expander("🔑 Anthropic API Key", expanded=not bool(st.session_state.api_key)):
    ak = st.text_input("Cole sua API Key aqui (sk-ant-...)",
                        value=st.session_state.api_key, type="password", key="ak_inp")
    if ak: st.session_state.api_key = ak
    if st.session_state.api_key:
        st.markdown('<div class="box-ok">🟢 IA ativa — mapeamento automático disponível</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="box-warn">🟡 Insira a API Key para usar o mapeamento automático por IA</div>',unsafe_allow_html=True)

st.divider()

# ═════════════════════════════════════════════════════════
# PASSO 1 — CLIENTES
# ═════════════════════════════════════════════════════════
if st.session_state.passo == 1:
    st.markdown('<div class="sec">👥 Clientes cadastrados</div>', unsafe_allow_html=True)
    clientes = listar()
    if not clientes:
        st.markdown('<div class="box-info">Nenhum cliente ainda. Clique em <b>➕ Novo</b> acima para começar.</div>',unsafe_allow_html=True)
    else:
        for c in clientes:
            c1,c2,c3,c4,c5,c6 = st.columns([3,1.5,1.5,1.5,1,1])
            c1.markdown(f"**{c['nome']}**")
            c2.markdown({"omie":"🟠 Omie","conta_azul":"🔵 Conta Azul","arquivo":"📄 Arquivo"}.get(c["tipo"],c["tipo"]))
            c3.markdown("✅ Mapeado" if c["mapeado"] else "⚠️ Pendente")
            c4.markdown(f"🕐 {c['at']}")
            if c5.button("Abrir", key=f"ab_{c['id']}"):
                st.session_state.cid = c["id"]
                st.session_state.arquivos_carregados = []
                st.session_state.df_consolidado = None
                st.session_state.sug_ia = None
                log(f"Cliente '{c['nome']}' selecionado")
                ir(3)
            if c6.button("🗑", key=f"del_{c['id']}"):
                p = path_perfil(c["id"])
                if os.path.exists(p): os.remove(p)
                if st.session_state.cid == c["id"]: st.session_state.cid = None
                log(f"Cliente excluído","warn"); st.rerun()
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
        st.markdown('<div class="box-info">📌 Omie → Configurações → API → Criar Aplicação → copie App Key e App Secret</div>',unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: ak_o = st.text_input("App Key",    type="password", key="nc_akey")
        with c2: as_o = st.text_input("App Secret", type="password", key="nc_asec")
    elif "Conta Azul" in tipo:
        st.markdown('<div class="box-info">📌 Conta Azul → Integrações → API → Gerar Token</div>',unsafe_allow_html=True)
        tok_ca = st.text_input("Access Token", type="password", key="nc_tok")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ Cadastrar Cliente", use_container_width=True, key="btn_cad"):
        if not nome.strip():
            st.error("Informe o nome da empresa.")
        else:
            tk = "arquivo" if "Arquivo" in tipo else ("omie" if "Omie" in tipo else "conta_azul")
            cid = gerar_id(nome)
            creds = {}
            if tk == "omie":        creds = {"app_key":ak_o,"app_secret":as_o}
            elif tk == "conta_azul": creds = {"access_token":tok_ca}
            salvar(cid, {"nome":nome.strip(),"tipo":tk,"credenciais":creds,"mapeamento":{}})
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
# PASSO 3 — IMPORTAR (MÚLTIPLOS ARQUIVOS)
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 3:
    if not st.session_state.cid:
        st.markdown('<div class="box-warn">⚠️ Cadastre ou selecione um cliente primeiro (➕ Novo ou 👥 Clientes).</div>',unsafe_allow_html=True)
        st.stop()

    perf = carregar(st.session_state.cid)
    tipo = perf.get("tipo","arquivo")
    creds = perf.get("credenciais",{})

    st.markdown(f'<div class="sec">🔗 Importar dados — {perf.get("nome","")}</div>',unsafe_allow_html=True)

    # ── ARQUIVO (MÚLTIPLOS) ──────────────────────────────
    if tipo == "arquivo":

        st.markdown("""
        <div class="box-info">
        📂 Envie <b>um ou mais arquivos</b> do cliente — PDF, Excel ou CSV.<br>
        Pode enviar a DRE num arquivo, o Balanço em outro, o Fluxo de Caixa em outro.<br>
        O sistema consolida tudo automaticamente.
        </div>""", unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Selecione os arquivos (pode selecionar múltiplos de uma vez)",
            type=["pdf","xlsx","xls","xlsm","csv"],
            accept_multiple_files=True,
            key="up_multi"
        )

        # Processa novos uploads
        if uploaded_files:
            nomes_ja_carregados = {a["nome"] for a in st.session_state.arquivos_carregados}
            novos = [f for f in uploaded_files if f.name not in nomes_ja_carregados]

            for f in novos:
                with st.spinner(f"Lendo {f.name}..."):
                    df, msg_r = ler_arquivo(f.read(), f.name)
                if df is not None:
                    st.session_state.arquivos_carregados.append({
                        "nome": f.name,
                        "df": df,
                        "linhas": len(df),
                        "colunas": df.shape[1],
                        "ok": True,
                        "msg": msg_r
                    })
                    log(f"'{f.name}' carregado: {msg_r}")
                else:
                    st.session_state.arquivos_carregados.append({
                        "nome": f.name, "df": None,
                        "linhas": 0, "colunas": 0,
                        "ok": False, "msg": msg_r
                    })
                    log(f"Erro em '{f.name}': {msg_r}", "err")

        # Lista de arquivos carregados
        if st.session_state.arquivos_carregados:
            st.markdown('<div class="sec">📂 Arquivos carregados</div>', unsafe_allow_html=True)

            for i, arq in enumerate(st.session_state.arquivos_carregados):
                c1,c2,c3,c4,c5 = st.columns([3,1.2,1.2,1.2,0.8])
                with c1:
                    icone = "📄" if arq["nome"].endswith((".xlsx",".xls")) else ("📋" if arq["nome"].endswith(".csv") else "📑")
                    st.markdown(f"{icone} **{arq['nome']}**")
                with c2:
                    st.markdown(f"{'✅' if arq['ok'] else '❌'} {arq['linhas']} linhas")
                with c3:
                    st.markdown(f"🔢 {arq['colunas']} colunas")
                with c4:
                    st.markdown(f"{'<span class=\"arq-status-ok\">Lido</span>' if arq['ok'] else '<span class=\"arq-status-err\">Erro</span>'}",
                                unsafe_allow_html=True)
                with c5:
                    if st.button("🗑", key=f"rem_arq_{i}", help="Remover"):
                        st.session_state.arquivos_carregados.pop(i)
                        st.session_state.df_consolidado = None
                        st.rerun()
                st.divider()

            # Resumo
            ok_count = sum(1 for a in st.session_state.arquivos_carregados if a["ok"])
            total_cols = sum(a["colunas"] for a in st.session_state.arquivos_carregados if a["ok"])
            st.markdown(f'<div class="box-ok">✅ <b>{ok_count} arquivo(s)</b> carregado(s) · <b>{total_cols} colunas</b> no total disponíveis para mapeamento</div>',unsafe_allow_html=True)

            # Consolida e mostra preview
            dfs_ok = [a["df"] for a in st.session_state.arquivos_carregados if a["ok"] and a["df"] is not None]
            if dfs_ok:
                df_cons = consolidar_arquivos(dfs_ok)
                st.session_state.df_consolidado = df_cons

                with st.expander(f"👁 Preview consolidado ({len(df_cons)} linhas × {df_cons.shape[1]} colunas)"):
                    st.dataframe(df_cons.head(8), use_container_width=True)

            # Botões de ação
            st.markdown("<br>", unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            with c1:
                if st.button("🤖 Mapear com IA →", use_container_width=True, key="btn_ir_map"):
                    if st.session_state.df_consolidado is not None:
                        st.session_state.sug_ia = None
                        ir(4)
                    else:
                        st.error("Nenhum arquivo válido carregado.")
            with c2:
                if perf.get("mapeamento"):
                    if st.button("⚡ Usar mapeamento salvo →", use_container_width=True, key="btn_salvo"):
                        st.session_state.mapa = perf["mapeamento"]
                        log("Mapeamento salvo aplicado")
                        ir(5)
        else:
            st.markdown('<div class="box-info">⬆️ Selecione os arquivos acima para começar.</div>',unsafe_allow_html=True)

    # ── OMIE ────────────────────────────────────────────
    elif tipo == "omie":
        st.markdown('<div class="box-info">Busque os dados diretamente do Omie por período.</div>',unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        with c1: ano_o = st.selectbox("Ano", list(range(2020,2031)), index=4, key="ano_om")
        with c2: mes_o = st.selectbox("Mês de início", list(range(1,13)), format_func=num_mes, key="mes_om")
        with c3: mes_f = st.selectbox("Mês de fim", list(range(1,13)), format_func=num_mes, index=min(mes_o,12)-1, key="mes_om_f")

        if st.button("🔍 Buscar dados do Omie", use_container_width=True, key="btn_omie"):
            k = creds.get("app_key",""); s = creds.get("app_secret","")
            dfs = []; errs = []
            rng = list(range(mes_o, mes_f+1)) if mes_f >= mes_o else [mes_o]
            pb = st.progress(0)
            with st.spinner(f"Buscando {len(rng)} mês/meses do Omie..."):
                for i,m in enumerate(rng):
                    df_m,e = omie_mes(k,s,ano_o,m); dfs.append(df_m); errs+=e
                    pb.progress((i+1)/len(rng))
            df_om = pd.concat(dfs, ignore_index=True)
            st.session_state.df_consolidado = df_om
            st.session_state.arquivos_carregados = [{"nome":f"Omie {ano_o}","df":df_om,"linhas":len(df_om),"colunas":df_om.shape[1],"ok":True,"msg":"Omie API"}]
            st.markdown(f'<div class="box-ok">✅ {len(df_om)} meses importados do Omie.</div>',unsafe_allow_html=True)
            st.dataframe(df_om.T, use_container_width=True)
            log(f"Omie: {len(df_om)} meses")
            if errs: st.warning(" | ".join(errs[:3]))
            c1,c2 = st.columns(2)
            with c1:
                if st.button("🤖 Mapear com IA →", use_container_width=True, key="btn_map_om"):
                    st.session_state.sug_ia = None; ir(4)
            with c2:
                if perf.get("mapeamento"):
                    if st.button("⚡ Usar mapeamento salvo →", use_container_width=True, key="btn_salvo_om"):
                        st.session_state.mapa = perf["mapeamento"]; ir(5)

    # ── CONTA AZUL ──────────────────────────────────────
    elif tipo == "conta_azul":
        st.markdown('<div class="box-info">Busque os dados do Conta Azul.</div>',unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: ano_ca = st.selectbox("Ano", list(range(2020,2031)), index=4, key="ano_ca3")
        with c2: mes_ca = st.selectbox("Mês", list(range(1,13)), format_func=num_mes, key="mes_ca3")
        if st.button("🔍 Buscar dados Conta Azul", use_container_width=True, key="btn_ca"):
            tok = creds.get("access_token","")
            with st.spinner("Conectando..."): df_ca = ca_mes(tok,ano_ca,mes_ca)
            st.session_state.df_consolidado = df_ca
            st.session_state.arquivos_carregados = [{"nome":f"ContaAzul {ano_ca}","df":df_ca,"linhas":len(df_ca),"colunas":df_ca.shape[1],"ok":True,"msg":"Conta Azul API"}]
            st.markdown('<div class="box-ok">✅ Dados Conta Azul importados.</div>',unsafe_allow_html=True)
            st.dataframe(df_ca.T, use_container_width=True)
            log("Conta Azul importado")
            if st.button("🤖 Mapear com IA →", use_container_width=True, key="btn_map_ca"):
                st.session_state.sug_ia = None; ir(4)

# ═════════════════════════════════════════════════════════
# PASSO 4 — MAPEAR COM IA
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 4:
    if not st.session_state.cid:
        st.markdown('<div class="box-warn">⚠️ Selecione um cliente primeiro.</div>',unsafe_allow_html=True); st.stop()
    if st.session_state.df_consolidado is None:
        st.markdown('<div class="box-warn">⚠️ Importe os dados primeiro (🔗 Importar).</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid)
    df   = st.session_state.df_consolidado

    st.markdown(f'<div class="sec">🤖 Mapeamento DE → PARA — {perf.get("nome","")}</div>',unsafe_allow_html=True)

    # Resumo dos arquivos que vieram
    arqs = st.session_state.arquivos_carregados
    if arqs:
        st.markdown(f'<div class="box-info">📂 <b>{len(arqs)} arquivo(s)</b> consolidados · <b>{df.shape[1]} colunas</b> · <b>{len(df)} linhas</b> disponíveis para mapear</div>',unsafe_allow_html=True)

    if not st.session_state.sug_ia:
        if perf.get("mapeamento"):
            st.markdown('<div class="box-ok">✅ Este cliente já possui mapeamento salvo.</div>',unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            with c1:
                if st.button("📂 Carregar mapeamento salvo", use_container_width=True, key="btn_load"):
                    mp = perf["mapeamento"]
                    fake = {"mapeamento":{col:{"campo":can,"confianca":100,"motivo":"Mapeamento salvo"} for col,can in mp.items()}}
                    st.session_state.sug_ia = fake
                    st.session_state.mapa = mp
                    log("Mapeamento salvo carregado"); st.rerun()
            with c2:
                if st.button("🤖 Refazer com IA", use_container_width=True, key="btn_refaz"):
                    if not st.session_state.api_key: st.error("Insira a API Key acima.")
                    else:
                        with st.spinner("🤖 Claude analisando todos os arquivos..."): res = mapear_ia(df, st.session_state.api_key)
                        if "erro" in res: st.error(res["erro"])
                        else:
                            st.session_state.sug_ia = res
                            st.session_state.mapa = {c:i.get("campo") for c,i in res.get("mapeamento",{}).items() if i.get("campo")}
                            log(f"IA mapeou {len(st.session_state.mapa)} colunas"); st.rerun()
        else:
            if not st.session_state.api_key:
                st.markdown('<div class="box-warn">⚠️ Insira a Anthropic API Key no campo acima para usar a IA.</div>',unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="box-info">A IA vai analisar <b>{df.shape[1]} colunas</b> de <b>{len(arqs)} arquivo(s)</b> e sugerir o mapeamento automaticamente.</div>',unsafe_allow_html=True)
                if st.button("🤖 Analisar com IA agora", use_container_width=True, key="btn_ia"):
                    with st.spinner("🤖 Claude analisando colunas... (10–20 seg)"): res = mapear_ia(df, st.session_state.api_key)
                    if "erro" in res: st.error(f"Erro: {res['erro']}")
                    else:
                        st.session_state.sug_ia = res
                        st.session_state.mapa = {c:i.get("campo") for c,i in res.get("mapeamento",{}).items() if i.get("campo")}
                        log(f"IA mapeou {len(st.session_state.mapa)} colunas"); st.rerun()
    else:
        sug = st.session_state.sug_ia.get("mapeamento",{})
        alta  = sum(1 for v in sug.values() if v.get("confianca",0) >= 85)
        media = sum(1 for v in sug.values() if 60 <= v.get("confianca",0) < 85)
        baixa = sum(1 for v in sug.values() if v.get("confianca",0) < 60)

        ca,cb,cc,cd = st.columns(4)
        ca.markdown(f'<div class="card"><div class="card-label">Colunas analisadas</div><div class="kpi">{len(sug)}</div></div>',unsafe_allow_html=True)
        cb.markdown(f'<div class="card"><div class="card-label">✅ Alta ≥85%</div><div class="kpi g">{alta}</div></div>',unsafe_allow_html=True)
        cc.markdown(f'<div class="card"><div class="card-label">⚠️ Média 60–84%</div><div class="kpi o">{media}</div></div>',unsafe_allow_html=True)
        cd.markdown(f'<div class="card"><div class="card-label">❗ Revisar &lt;60%</div><div class="kpi r">{baixa}</div></div>',unsafe_allow_html=True)

        st.markdown('<div class="box-info">✅ Verde = aprovado automaticamente · ⚠️ Amarelo e ❗ Vermelho = revise você</div>',unsafe_allow_html=True)

        filtro = st.radio("Mostrar:", ["Todas as colunas","Apenas para revisar (<85%)","Apenas não mapeadas"],
                          horizontal=True, key="filtro_m")
        opcoes = ["(ignorar)"] + LISTA_CAMPOS
        novo_mapa = {}

        for col_c, info in sug.items():
            conf = info.get("confianca",0)
            campo_ia = info.get("campo")
            mot = info.get("motivo","")

            if filtro == "Apenas para revisar (<85%)" and conf >= 85:
                novo_mapa[col_c] = campo_ia; continue
            if filtro == "Apenas não mapeadas" and campo_ia:
                novo_mapa[col_c] = campo_ia; continue

            badge = (f'<span class="b-ok">✅ {conf}%</span>' if conf >= 85 else
                     f'<span class="b-warn">⚠️ {conf}%</span>' if conf >= 60 else
                     f'<span class="b-err">❗ {conf}%</span>')

            c1,c2,c3 = st.columns([2,2.5,3])
            with c1:
                st.markdown(f"**{col_c}**")
                st.markdown(badge, unsafe_allow_html=True)
            with c2:
                idx = opcoes.index(campo_ia) if campo_ia in opcoes else 0
                esc = st.selectbox("", opcoes, index=idx, key=f"mp_{col_c}", label_visibility="collapsed")
                if esc != "(ignorar)": novo_mapa[col_c] = esc
            with c3:
                st.caption(mot)
            st.divider()

        faltando = [c for c in LISTA_CAMPOS if c not in set(novo_mapa.values())]
        if faltando:
            with st.expander(f"ℹ️ {len(faltando)} campos sem dado (ficarão como zero no cálculo)"):
                for f in faltando: st.caption(f"• {f} ({CAMPOS[f]['g']})")

        st.divider()
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("💾 Salvar mapeamento", use_container_width=True, key="btn_salvar"):
                st.session_state.mapa = novo_mapa
                pa = carregar(st.session_state.cid) or {}
                pa["mapeamento"] = novo_mapa; salvar(st.session_state.cid, pa)
                log(f"Mapeamento salvo: {len(novo_mapa)} campos")
                st.success(f"✅ Salvo! {len(novo_mapa)} campos mapeados.")
        with c2:
            if st.button("▶️ Processar agora →", use_container_width=True, key="btn_proc"):
                st.session_state.mapa = novo_mapa
                pa = carregar(st.session_state.cid) or {}
                pa["mapeamento"] = novo_mapa; salvar(st.session_state.cid, pa)
                log("Processando..."); ir(5)
        with c3:
            if st.button("🔄 Refazer com IA", use_container_width=True, key="btn_ref2"):
                st.session_state.sug_ia = None; st.rerun()

# ═════════════════════════════════════════════════════════
# PASSO 5 — PROCESSAR
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 5:
    if not st.session_state.cid:
        st.markdown('<div class="box-warn">⚠️ Selecione um cliente.</div>',unsafe_allow_html=True); st.stop()
    if st.session_state.df_consolidado is None:
        st.markdown('<div class="box-warn">⚠️ Importe dados (🔗 Importar).</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid)
    mapa = st.session_state.mapa or perf.get("mapeamento",{})
    st.markdown(f'<div class="sec">⚙️ Processar — {perf.get("nome","")}</div>',unsafe_allow_html=True)

    if not mapa:
        st.markdown('<div class="box-warn">⚠️ Sem mapeamento. Vá para 🤖 Mapear.</div>',unsafe_allow_html=True); st.stop()

    st.markdown(f'<div class="box-info">Mapeamento com <b>{len(mapa)}</b> campos · <b>{len(st.session_state.df_consolidado)}</b> linhas</div>',unsafe_allow_html=True)

    if st.button("⚙️ Calcular todos os indicadores", use_container_width=True, key="btn_calc"):
        with st.spinner("Calculando..."):
            df_can = aplicar_mapa(st.session_state.df_consolidado, mapa)
            df_fin = calcular(df_can)
            st.session_state.df_final = df_fin
        log("Indicadores calculados")
        st.success("✅ Processamento concluído!")

    if st.session_state.df_final is not None:
        df_r = st.session_state.df_final
        ul = df_r.iloc[-1] if len(df_r) > 0 else {}

        st.markdown('<div class="sec">KPIs — último período</div>',unsafe_allow_html=True)
        def kcard(label, campo, pct=False, dec=False):
            v = ul.get(campo,0)
            try:
                vf = float(v); cls = "g" if vf >= 0 else "r"
                txt = f"{vf*100:.1f}%" if pct else (f"{vf:.2f}" if dec else fmt_brl(vf))
            except: txt,cls = "—",""
            return f'<div class="card"><div class="card-label">{label}</div><div class="kpi {cls}">{txt}</div></div>'

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.markdown(kcard("Receita Bruta","receita bruta de vendas"),unsafe_allow_html=True)
        c2.markdown(kcard("Rec. Líquida","receita líquida de vendas"),unsafe_allow_html=True)
        c3.markdown(kcard("Lucro Bruto","lucro bruto"),unsafe_allow_html=True)
        c4.markdown(kcard("Lucro Líquido","lucro líquido"),unsafe_allow_html=True)
        c5.markdown(kcard("EBITDA","EBITDA",pct=True),unsafe_allow_html=True)
        c6.markdown(kcard("Kanitz","termômetro de kanitz",dec=True),unsafe_allow_html=True)

        t1,t2,t3 = st.tabs(["📊 DRE Resumida","🏦 Balanço","📋 Todos os campos"])
        with t1:
            dc = ["Ano","mês","receita bruta de vendas","receita líquida de vendas",
                  "lucro bruto","lucro operacional","lucro líquido","Lucratividade","EBITDA"]
            ex = [c for c in dc if c in df_r.columns]
            ds = df_r[ex].copy()
            for c in ["Lucratividade","EBITDA"]:
                if c in ds.columns: ds[c] = ds[c].apply(lambda x: f"{float(x)*100:.1f}%" if pd.notna(x) else "")
            st.dataframe(ds, use_container_width=True, height=350)
        with t2:
            bc = ["Ano","mês","ativo total saldo","ativo circulante saldo","passivo total saldo",
                  "passivo circulante saldo","patrimônio líquido","disponibilidades saldo",
                  "contas a receber saldo","contas a pagar de fornecedores saldo"]
            ex2 = [c for c in bc if c in df_r.columns]
            st.dataframe(df_r[ex2], use_container_width=True, height=350)
        with t3:
            st.dataframe(df_r, use_container_width=True, height=400)

        st.divider()
        if st.button("💾 Exportar →", key="btn_exp"): ir(6)

# ═════════════════════════════════════════════════════════
# PASSO 6 — EXPORTAR
# ═════════════════════════════════════════════════════════
elif st.session_state.passo == 6:
    st.markdown('<div class="sec">💾 Exportar para Power BI</div>',unsafe_allow_html=True)
    if st.session_state.df_final is None:
        st.markdown('<div class="box-warn">⚠️ Processe os dados primeiro (⚙️ Processar).</div>',unsafe_allow_html=True); st.stop()

    perf = carregar(st.session_state.cid) if st.session_state.cid else {}
    nome_e = perf.get("nome","dados"); nid = gerar_id(nome_e)
    df_exp = st.session_state.df_final.copy()
    if "Data" in df_exp.columns:
        df_exp["Data"] = pd.to_datetime(df_exp["Data"],errors="coerce").dt.strftime("%d/%m/%Y")
    for c in ["mês_num","_sheet"]:
        if c in df_exp.columns: df_exp.drop(columns=[c],inplace=True)

    st.markdown(f'<div class="card"><div class="card-label">Pronto para baixar</div><b>{len(df_exp)}</b> meses · <b>{df_exp.shape[1]}</b> colunas · Compatível com Power BI V2.csv</div>',unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1:
        csv = df_exp.to_csv(sep=";",decimal=",",index=False,encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 CSV para Power BI", csv,
                           file_name=f"{nid}_PowerBI.csv", mime="text/csv", use_container_width=True)
    with c2:
        buf = BytesIO()
        with pd.ExcelWriter(buf,engine="openpyxl") as w: df_exp.to_excel(w,index=False,sheet_name="Dados")
        buf.seek(0)
        st.download_button("📥 Excel", buf.getvalue(),
                           file_name=f"{nid}_dados.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with c3:
        jout = df_exp.to_json(orient="records",force_ascii=False,indent=2)
        st.download_button("📥 JSON", jout.encode(),
                           file_name=f"{nid}_dados.json", mime="application/json", use_container_width=True)

    st.divider()
    st.markdown('<div class="sec">Resumo por ano</div>',unsafe_allow_html=True)
    if "Ano" in df_exp.columns:
        anos = sorted(df_exp["Ano"].dropna().unique())
        cols_a = st.columns(min(len(anos),4))
        for i,ano in enumerate(anos):
            dfa = df_exp[df_exp["Ano"]==ano]
            rec = pd.to_numeric(dfa.get("receita bruta de vendas",pd.Series([0])),errors="coerce").sum()
            ll  = pd.to_numeric(dfa.get("lucro líquido",pd.Series([0])),errors="coerce").sum()
            m   = (ll/rec*100) if rec > 0 else 0; cls = "g" if ll >= 0 else "r"
            with cols_a[i%4]:
                st.markdown(
                    f'<div class="card"><div class="card-label">{int(ano)}</div>'
                    f'Receita: <b>{fmt_brl(rec)}</b><br>'
                    f'Lucro: <b class="kpi {cls}" style="font-size:1rem">{fmt_brl(ll)}</b><br>'
                    f'Margem: <b>{m:.1f}%</b></div>',unsafe_allow_html=True)

    st.markdown('<div class="box-ok">✅ Substitua o CSV na pasta do Power BI e clique em Atualizar no relatório.</div>',unsafe_allow_html=True)

    if st.session_state.log:
        st.divider()
        with st.expander("📋 Log de operações"):
            for l in st.session_state.log[:20]: st.caption(l)
