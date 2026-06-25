"""
NetExame Analytics BI — v8
Rodar: streamlit run analytics_bi.py
pip install streamlit pandas numpy scikit-learn statsmodels plotly openpyxl pdfplumber requests anthropic openai
pip install prophet  (opcional)
"""
import streamlit as st
import pandas as pd
import base64
import numpy as np
import json, os, re, io, requests, time, warnings
from io import BytesIO
from datetime import datetime
import plotly.graph_objects as go

warnings.filterwarnings("ignore")

try:
    from openai import OpenAI; OPENAI_OK = True
except: OPENAI_OK = False
try:
    import anthropic; ANTHROPIC_OK = True
except: ANTHROPIC_OK = False
try:
    import pdfplumber; PDF_OK = True
except: PDF_OK = False
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from sklearn.metrics import mean_squared_error
    STATS_OK = True
except: STATS_OK = False
try:
    from prophet import Prophet; PROPHET_OK = True
except: PROPHET_OK = False

# ═══════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════
st.set_page_config(
    page_title="NetExame Analytics BI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""<style>
.stApp{background:#F8F9FC;}
.mc{background:white;border:1px solid #E8ECF0;border-radius:12px;padding:16px 18px;
  text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.mc-lbl{font-size:.62rem;text-transform:uppercase;letter-spacing:.1em;
  color:#9CA3AF;font-weight:600;margin-bottom:7px;}
.mc-val{font-size:1.35rem;font-weight:700;color:#111827;}
.mc-val.g{color:#059669;}.mc-val.r{color:#DC2626;}.mc-val.y{color:#D97706;}.mc-val.b{color:#2563EB;}
.mc-sub{font-size:.7rem;color:#9CA3AF;margin-top:3px;}
.phdr{background:white;border:1px solid #E8ECF0;border-radius:14px;
  padding:22px 28px;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.phdr h1{color:#111827!important;font-size:1.6rem;margin:0;}
.phdr p{color:#6B7280;margin:0;font-size:.86rem;}
.sec{font-size:.95rem;font-weight:700;color:#111827;
  padding-left:11px;border-left:3px solid #2563EB;margin:20px 0 12px;}
.al-d{background:#FEF2F2;border:1px solid #FECACA;border-radius:9px;
  padding:10px 14px;color:#DC2626;font-size:.83rem;margin:4px 0;}
.al-w{background:#FFFBEB;border:1px solid #FDE68A;border-radius:9px;
  padding:10px 14px;color:#D97706;font-size:.83rem;margin:4px 0;}
.al-s{background:#ECFDF5;border:1px solid #A7F3D0;border-radius:9px;
  padding:10px 14px;color:#059669;font-size:.83rem;margin:4px 0;}
.al-i{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:9px;
  padding:10px 14px;color:#2563EB;font-size:.83rem;margin:4px 0;}
.kz-s{background:#ECFDF5;border:1px solid #A7F3D0;border-radius:10px;padding:12px 16px;}
.kz-w{background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;padding:12px 16px;}
.kz-d{background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:12px 16px;}
.dre-wrap{overflow-x:auto;border-radius:10px;border:1px solid #E8ECF0;margin-top:8px;}
table.dre{width:100%;border-collapse:collapse;font-size:.76rem;}
table.dre th{background:#F3F4F6;color:#6B7280;padding:7px 10px;text-align:right;
  font-weight:600;border-bottom:1px solid #E8ECF0;white-space:nowrap;}
table.dre th:first-child{text-align:left;min-width:180px;}
table.dre td{padding:5px 10px;text-align:right;color:#374151;white-space:nowrap;}
table.dre td:first-child{text-align:left;color:#111827;}
table.dre tr.cat td{background:#F9FAFB;color:#6B7280!important;
  font-size:.67rem;text-transform:uppercase;font-weight:600;}
table.dre tr.sub td{background:#FAFAFA;}
table.dre tr.tot td{background:#F3F4F6;font-weight:700;}
table.dre tr.tot td:first-child{color:#2563EB!important;}
table.dre tr.pct td:not(:first-child){color:#D97706!important;}
table.dre td.pos{color:#059669!important;}
table.dre td.neg{color:#DC2626!important;}
table.dre td.neu{color:#9CA3AF!important;}
table.dre tr:hover td{background:#F9FAFB!important;}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════
PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clientes_bi")
CFG   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
os.makedirs(PASTA, exist_ok=True)

MESES   = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
MES_NUM = {m:str(i+1).zfill(2) for i,m in enumerate(MESES)}

DEMONSTRACOES_CAMPOS = {
    "DRE": ["receita bruta de vendas","impostos sobre vendas","devoluções de vendas",
            "CMV (custo da mercadoria vendida)","despesas comerciais","despesas administrativas",
            "despesas financeiras líquidas","despesas com depreciações e amortizações",
            "receitas não operacionais","despesas não operacionais",
            "provisão para imposto de renda","provisão para contribuição social",
            "numero de vendas","pró-labore/distribuição de lucro"],
    "Balanço": ["disponibilidades saldo","contas a receber saldo",
            "estoque inicial do mês de mercadorias para revenda saldo",
            "estoque final do mês de mercadorias para revenda saldo","Outros AC","Ativo NC",
            "contas a pagar de fornecedores saldo","Passivos Financeiros","Outros PC","Passivo NC","Aporte"],
    "Fluxo": ["Disponibilidades entradas","Disponibilidades Saida",
            "Centro de Custos Entradas 1","Centro de Custos Entradas 2",
            "Centro de Custos Entradas 3","Centro de Custos Entradas 4",
            "Centro de Custos Saidas 1","Centro de Custos Saidas 2",
            "Centro de Custos Saidas 3","Centro de Custos Saidas 4"],
}

CAMPOS_DRE = ["receita bruta de vendas","impostos sobre vendas","devoluções de vendas",
    "CMV (custo da mercadoria vendida)","estoque inicial do mês de mercadorias para revenda saldo",
    "estoque final do mês de mercadorias para revenda saldo","despesas comerciais",
    "despesas administrativas","despesas financeiras líquidas",
    "despesas com depreciações e amortizações","receitas não operacionais",
    "despesas não operacionais","provisão para imposto de renda",
    "provisão para contribuição social","numero de vendas","pró-labore/distribuição de lucro"]
CAMPOS_BAL = ["disponibilidades saldo","contas a receber saldo",
    "estoque final do mês de mercadorias para revenda saldo","Outros AC","Ativo NC",
    "contas a pagar de fornecedores saldo","Passivos Financeiros","Outros PC","Passivo NC","Aporte"]
CAMPOS_FLUXO = ["Disponibilidades entradas","Disponibilidades Saida",
    "Centro de Custos Entradas 1","Centro de Custos Entradas 2",
    "Centro de Custos Entradas 3","Centro de Custos Entradas 4",
    "Centro de Custos Saidas 1","Centro de Custos Saidas 2",
    "Centro de Custos Saidas 3","Centro de Custos Saidas 4"]
TODOS = list(dict.fromkeys(CAMPOS_DRE + CAMPOS_BAL + CAMPOS_FLUXO))
MODELOS_ML = {"ARIMA":STATS_OK,"ExponentialSmoothing":STATS_OK,
              "SARIMAX":STATS_OK,"Holt":STATS_OK,"Prophet":PROPHET_OK}
CORES = ["#2176FF","#00D4AA","#FFB627","#F85149","#A371F7","#F78166","#79C0FF","#56D364"]

# ═══════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════
def fmt(v, t="brl"):
    try:
        f=float(v)
        if t=="brl":
            s="-" if f<0 else ""; f=abs(f)
            if f>=1e6: return f"{s}R$ {f/1e6:.1f}M"
            if f>=1e3: return f"{s}R$ {f/1e3:.0f}K"
            return f"{s}R$ {f:.0f}"
        if t=="pct": return f"{f:.1f}%"
        if t=="x":   return f"{f:.2f}x"
        if t=="d":   return f"{f:.0f}d"
    except: pass
    return "—"

def safe(a,b,d=0.):
    try: a,b=float(a),float(b); return a/b if b else d
    except: return d

def gid(n):
    import unicodedata
    s=unicodedata.normalize("NFKD",n.lower())
    s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+","_",s).strip("_")[:40]

def cor(v, inv=False):
    try:
        f=float(v)
        if inv: return "r" if f>0 else ("g" if f<0 else "")
        return "g" if f>0 else ("r" if f<0 else "")
    except: return ""

def cn(df,c):
    if c in df.columns: return pd.to_numeric(df[c],errors="coerce").fillna(0.)
    return pd.Series(0.,index=df.index)

def cm_(df): return next((c for c in df.columns if c.lower().strip() in ["mês","mes"]),None)
def ca_(df): return next((c for c in df.columns if c.lower().strip() in ["ano","year"]),None)

# ═══════════════════════════════════════════════════
# PERSISTÊNCIA
# ═══════════════════════════════════════════════════
def load_cfg():
    try:
        with open(CFG,encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_cfg(d):
    try:
        with open(CFG,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    except: pass

def path_cli(cid): return os.path.join(PASTA,f"{gid(cid)}.json")

def salvar_cli(cid,d):
    d.setdefault("meta",{})["at"]=datetime.now().isoformat()
    with open(path_cli(cid),"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)

def load_cli(cid):
    p=path_cli(cid)
    if not os.path.exists(p): return None
    with open(p,encoding="utf-8") as f: return json.load(f)

SENHA_MASTER = "netexame2024"  # Troque para sua senha

def verificar_pin(cid, pin):
    p = load_cli(cid)
    if not p: return False
    pin_salvo = p.get("pin","")
    if not pin_salvo: return True  # sem pin = acesso livre
    return str(pin) == str(pin_salvo)

def ls_cli():
    out=[]
    for a in os.listdir(PASTA):
        if a.endswith(".json"):
            try:
                with open(os.path.join(PASTA,a),encoding="utf-8") as f: d=json.load(f)
                out.append({"id":a[:-5],"nome":d.get("nome","?"),"at":d.get("meta",{}).get("at","")[:10]})
            except: pass
    return sorted(out,key=lambda x:x["nome"].lower())

def save_df(cid,df):
    df.to_csv(os.path.join(PASTA,f"{gid(cid)}_dados.csv"),sep=";",decimal=",",index=False,encoding="utf-8-sig")

def load_df(cid):
    p=os.path.join(PASTA,f"{gid(cid)}_dados.csv")
    if not os.path.exists(p): return None
    try: return pd.read_csv(p,sep=";",decimal=",",encoding="utf-8-sig")
    except: return None

# ═══════════════════════════════════════════════════
# LEITURA
# ═══════════════════════════════════════════════════
def limpar(df):
    cols,cnt=[],{}
    for c in df.columns:
        s=str(c).strip()
        if s.lower() in ["nan","none",""]: s=f"__c{len(cols)}"
        if s in cnt: cnt[s]+=1; s=f"{s}_{cnt[s]}"
        else: cnt[s]=0
        cols.append(s)
    df.columns=cols
    df=df.dropna(how="all").dropna(axis=1,how="all")
    df=df[[c for c in df.columns if not c.startswith("__c")]]
    return df.reset_index(drop=True)

def ler(b,nome):
    n=nome.lower()
    try:
        if n.endswith(".pdf"):
            if not PDF_OK: return None,"pip install pdfplumber"
            dfs=[]
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                for pg in pdf.pages:
                    for t in pg.extract_tables() or []:
                        if t and len(t)>1:
                            try: dfs.append(pd.DataFrame(t[1:],columns=t[0]))
                            except: pass
            if not dfs: return None,"Sem tabelas no PDF"
            return limpar(pd.concat(dfs,ignore_index=True)),"PDF lido"
        elif n.endswith((".xlsx",".xls",".xlsm")):
            xls=pd.read_excel(io.BytesIO(b),sheet_name=None)
            dfs=[(s,df) for s,df in xls.items() if not df.dropna(how="all").empty]
            if not dfs: return None,"Excel vazio"
            dfs.sort(key=lambda x:len(x[1]),reverse=True)
            s,df=dfs[0]; return limpar(df),f"Excel — '{s}'"
        else:
            for enc in ["utf-8-sig","utf-8","latin1","cp1252"]:
                for sep in [";",",","\t","|"]:
                    try:
                        df=pd.read_csv(io.BytesIO(b),sep=sep,encoding=enc,on_bad_lines="skip",decimal=",")
                        if df.shape[1]>=2: return limpar(df),"CSV lido"
                    except: pass
            return None,"Não foi possível ler"
    except Exception as e: return None,str(e)

# ═══════════════════════════════════════════════════
# IA
# ═══════════════════════════════════════════════════
def eh_formato_longo(df):
    """Detecta se o arquivo está no formato vertical: uma coluna Ano, uma Mês, uma Conta, uma Valor."""
    cols_lower=[str(c).lower().strip() for c in df.columns]
    tem_ano="ano" in cols_lower or "year" in cols_lower
    tem_mes="mês" in cols_lower or "mes" in cols_lower or "month" in cols_lower
    tem_conta=any(c in cols_lower for c in ["conta","descrição","descricao","item"])
    tem_valor=any(c in cols_lower for c in ["valor","value","montante"])
    return tem_ano and tem_mes and tem_conta and tem_valor

def parser_formato_longo(df, tipo):
    """Parser determinístico para formato vertical (1 linha = 1 valor).
    Sempre confiável, não depende de IA, não trunca, sempre converte valores para positivo."""
    cols_lower={str(c).lower().strip():c for c in df.columns}
    col_ano=cols_lower.get("ano") or cols_lower.get("year")
    col_mes=cols_lower.get("mês") or cols_lower.get("mes") or cols_lower.get("month")
    col_conta=cols_lower.get("conta") or cols_lower.get("descrição") or cols_lower.get("descricao") or cols_lower.get("item")
    col_valor=cols_lower.get("valor") or cols_lower.get("value") or cols_lower.get("montante")
    if not all([col_ano,col_mes,col_conta,col_valor]):
        return []

    meses_pt={"jan":"jan","fev":"fev","mar":"mar","abr":"abr","mai":"mai","jun":"jun",
               "jul":"jul","ago":"ago","set":"set","out":"out","nov":"nov","dez":"dez",
               "janeiro":"jan","fevereiro":"fev","março":"mar","abril":"abr","maio":"mai",
               "junho":"jun","julho":"jul","agosto":"ago","setembro":"set",
               "outubro":"out","novembro":"nov","dezembro":"dez"}

    if tipo=="DRE":
        mapa={
            "receita bruta":"receita bruta de vendas","faturamento":"receita bruta de vendas",
            "receita de vendas":"receita bruta de vendas","receita de serviço":"receita bruta de vendas",
            "serviços recorrentes":"receita bruta de vendas","serviços avulsos":"receita bruta de vendas",
            "venda de mercadorias":"receita bruta de vendas","vendas brutas":"receita bruta de vendas",
            "outras receitas operacionais":"receita bruta de vendas",
            "imposto sobre vendas":"impostos sobre vendas","deduç":"impostos sobre vendas",
            "devoluç":"devoluções de vendas","desconto concedido":"devoluções de vendas",
            "cmv":"CMV (custo da mercadoria vendida)","custo da mercadoria":"CMV (custo da mercadoria vendida)",
            "custo do produto":"CMV (custo da mercadoria vendida)","custo variável":"CMV (custo da mercadoria vendida)",
            "mão de obra direta":"CMV (custo da mercadoria vendida)","materiais e insumos":"CMV (custo da mercadoria vendida)",
            "fretes de produção":"CMV (custo da mercadoria vendida)",
            "despesas comerciais":"despesas comerciais","salários comerciais":"despesas comerciais",
            "comissões":"despesas comerciais","marketing":"despesas comerciais","viagens comerciais":"despesas comerciais",
            "despesas administrativas":"despesas administrativas","salários administrativos":"despesas administrativas",
            "pró-labore":"despesas administrativas","aluguel":"despesas administrativas",
            "energia elétrica":"despesas administrativas","internet e telefonia":"despesas administrativas",
            "contabilidade":"despesas administrativas","sistemas e licenças":"despesas administrativas",
            "material de escritório":"despesas administrativas","manutenção":"despesas administrativas",
            "seguros":"despesas administrativas","treinamentos":"despesas administrativas",
            "despesas financeiras":"despesas financeiras líquidas","juros bancários":"despesas financeiras líquidas",
            "tarifas bancárias":"despesas financeiras líquidas",
            "receitas financeiras":"receitas não operacionais","juros ativos":"receitas não operacionais",
            "deprecia":"despesas com depreciações e amortizações",
            "irpj":"provisão para imposto de renda","csll":"provisão para contribuição social",
        }
    elif tipo=="BALANCO":
        mapa={
            "caixa":"disponibilidades saldo","banco":"disponibilidades saldo","disponib":"disponibilidades saldo",
            "aplicaç":"disponibilidades saldo","cliente":"contas a receber saldo","receber":"contas a receber saldo",
            "estoque":"estoque final do mês de mercadorias para revenda saldo",
            "impostos a recuperar":"Outros AC","outros ac":"Outros AC",
            "imobilizado":"Ativo NC","ativo nc":"Ativo NC",
            "fornecedor":"contas a pagar de fornecedores saldo",
            "empréstimos cp":"Passivos Financeiros","empréstimo cp":"Passivos Financeiros",
            "financiamentos cp":"Passivos Financeiros","financiamento":"Passivos Financeiros",
            "salários e encargos":"Outros PC","impostos a recolher":"Outros PC","outros pc":"Outros PC",
            "empréstimos lp":"Passivo NC","empréstimo lp":"Passivo NC",
            "financiamentos lp":"Passivo NC","passivo nc":"Passivo NC",
            "capital social":"PL","reservas":"PL",
            "lucros acumulados":"PL","resultado exercício":"PL","resultado do exercício":"PL",
        }
    elif tipo=="FLUXO":
        mapa={
            "receita serviç":"Centro de Custos Entradas 1",
            "receita produt":"Centro de Custos Entradas 2",
            "receb":"Centro de Custos Entradas 3",
            "receita financ":"Centro de Custos Entradas 4",
            "outras receitas":"Centro de Custos Entradas 4",
            "folha":"Centro de Custos Saidas 1",
            "fornecedor":"Centro de Custos Saidas 2",
            "impostos":"Centro de Custos Saidas 3",
            "desp. operac":"Centro de Custos Saidas 3",
            "despesas operac":"Centro de Custos Saidas 3",
            "investimentos":"Centro de Custos Saidas 4",
            "aluguel":"Centro de Custos Saidas 4",
            "saldo final":"disponibilidades saldo",
        }
    else:
        return []

    acumulado={}
    detalhamento=[]
    for _,row in df.iterrows():
        conta_raw=str(row.get(col_conta,"")).strip()
        conta=conta_raw.lower()
        ano=str(row.get(col_ano,"")).strip()
        mes_raw=str(row.get(col_mes,"")).lower().strip()[:3]
        mes=meses_pt.get(mes_raw,mes_raw)
        if not conta or not ano or not mes: continue
        campo_dest=None
        for k,v in mapa.items():
            if k in conta: campo_dest=v; break
        if not campo_dest: continue
        try:
            v=abs(float(row.get(col_valor,0)))
            chave=(ano,mes,campo_dest)
            acumulado[chave]=acumulado.get(chave,0)+v
            detalhamento.append({"ano":ano,"mes":mes,"campo_pai":campo_dest,
                                 "subconta":conta_raw,"valor":v})
        except: pass

    if tipo=="FLUXO":
        campos_entrada_fl=["Centro de Custos Entradas 1","Centro de Custos Entradas 2",
                           "Centro de Custos Entradas 3","Centro de Custos Entradas 4"]
        campos_saida_fl=["Centro de Custos Saidas 1","Centro de Custos Saidas 2",
                         "Centro de Custos Saidas 3","Centro de Custos Saidas 4"]
        periodos_vistos_fl=set((a,m) for (a,m,c) in acumulado.keys())
        for (ano_fl,mes_fl) in periodos_vistos_fl:
            soma_ent_fl=sum(acumulado.get((ano_fl,mes_fl,c),0) for c in campos_entrada_fl)
            soma_sai_fl=sum(acumulado.get((ano_fl,mes_fl,c),0) for c in campos_saida_fl)
            acumulado[(ano_fl,mes_fl,"Disponibilidades entradas")]=soma_ent_fl
            acumulado[(ano_fl,mes_fl,"Disponibilidades Saida")]=soma_sai_fl

    celulas=[{"ano":a,"mes":m,"campo":cp,"valor":v} for (a,m,cp),v in acumulado.items()]
    if detalhamento:
        celulas.append({"_detalhamento":detalhamento})
    return celulas

def detectar_tipo(df):
    cols_str=" ".join(str(c).lower() for c in df.columns)
    vals_str=" ".join(str(v).lower() for v in df.iloc[:,0].dropna().astype(str).tolist()[:20])
    # Se existir coluna "Conta" (formato longo), usa o conteúdo dela também — tem mais sinal
    col_conta=next((c for c in df.columns if str(c).lower().strip() in ["conta","descrição","descricao"]),None)
    vals_extra=""
    if col_conta is not None:
        vals_extra=" ".join(str(v).lower() for v in df[col_conta].dropna().astype(str).unique().tolist()[:60])
    txt=cols_str+" "+vals_str+" "+vals_extra

    # Conta pontos de evidência pra cada tipo, em vez de decidir pela primeira palavra encontrada
    pontos_dre=sum(1 for p in ["receita bruta","faturamento","cmv","custo da mercadoria",
                                "despesas comerciais","lucro bruto","lucro líquido","ebitda",
                                " dre","dre -","dre gerencial","receita líquida","receita liquida"] if p in txt)
    pontos_balanco=sum(1 for p in ["ativo","passivo","patrimônio líquido","caixa e banco",
                                     "clientes","estoque","fornecedor","imobilizado","capital social"] if p in txt)
    pontos_fluxo=sum(1 for p in ["entradas","saídas","total entradas","total saídas",
                                   "recebimento","pagamento","saldo acumulado"] if p in txt)

    pontos={"DRE":pontos_dre,"BALANCO":pontos_balanco,"FLUXO":pontos_fluxo}
    melhor=max(pontos,key=pontos.get)
    if pontos[melhor]==0: return "DESCONHECIDO"
    return melhor

def extrair_periodos_colunas(df):
    import re
    meses_pt={"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
               "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12,
               "janeiro":1,"fevereiro":2,"março":3,"abril":4,"maio":5,"junho":6,
               "julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12}
    periodos={}
    for col in df.columns:
        s=str(col).lower().strip()
        m=re.match(r'([a-zçã]+)[/\-\s](\d{2,4})',s)
        if m:
            mes_nome=m.group(1)[:3]
            ano_s=m.group(2)
            if mes_nome in meses_pt:
                ano=int(ano_s) if len(ano_s)==4 else 2000+int(ano_s)
                periodos[col]=(str(ano),mes_nome)
                continue
        for nome in meses_pt:
            if s.startswith(nome[:3]):
                periodos[col]=("?",nome[:3]); break
    return periodos

def parser_dre(df):
    periodos=extrair_periodos_colunas(df)
    if not periodos: return []
    import re as re_local
    ano_detectado=None
    for col in list(df.columns)[:3]:
        m=re_local.search(r'(20\d{2})',str(col))
        if m: ano_detectado=m.group(1); break
    if not ano_detectado:
        for val in df.iloc[:3].values.flatten():
            m=re_local.search(r'(20\d{2})',str(val))
            if m: ano_detectado=m.group(1); break
    if ano_detectado:
        periodos={col:(ano_detectado,mes) for col,(ano,mes) in periodos.items()}
    mapa={
        # Receitas
        "receita bruta":"receita bruta de vendas",
        "faturamento":"receita bruta de vendas",
        "receita da venda":"receita bruta de vendas",
        "serviços recorrentes":"receita bruta de vendas",
        "serviços avulsos":"receita bruta de vendas",
        "venda de mercadorias":"receita bruta de vendas",
        # Deduções
        "imposto sobre vendas":"impostos sobre vendas",
        "imposto":"impostos sobre vendas",
        "deduç":"impostos sobre vendas",
        "devoluç":"devoluções de vendas",
        "abatimento":"devoluções de vendas",
        # CMV / Custo Variável (soma de subcontas)
        "cmv":"CMV (custo da mercadoria vendida)",
        "custo da mercadoria":"CMV (custo da mercadoria vendida)",
        "custo dos serviços":"CMV (custo da mercadoria vendida)",
        "custo do produto":"CMV (custo da mercadoria vendida)",
        "custo variável":"CMV (custo da mercadoria vendida)",
        "insumos":"CMV (custo da mercadoria vendida)",
        "embalagem":"CMV (custo da mercadoria vendida)",
        "frete":"CMV (custo da mercadoria vendida)",
        # Despesas Comerciais
        "despesas comerciais":"despesas comerciais",
        "desp comerci":"despesas comerciais",
        "brindes":"despesas comerciais",
        "feiras e eventos":"despesas comerciais",
        "marketing":"despesas comerciais",
        # Despesas Administrativas (Pessoal + Estruturais + Administrativas)
        "despesas com pessoal":"despesas administrativas",
        "salários":"despesas administrativas",
        "encargos":"despesas administrativas",
        "benefícios":"despesas administrativas",
        "adicionais":"despesas administrativas",
        "despesas estruturais":"despesas administrativas",
        "aluguel":"despesas administrativas",
        "manutenção":"despesas administrativas",
        "infra tech":"despesas administrativas",
        "despesas administrativas":"despesas administrativas",
        "serviços adm":"despesas administrativas",
        "mat. escritorio":"despesas administrativas",
        "viagens e locomoção":"despesas administrativas",
        "desp admin":"despesas administrativas",
        # Despesas Financeiras
        "desp financ":"despesas financeiras líquidas",
        "juros pagos":"despesas financeiras líquidas",
        "juros recebidos":"receitas não operacionais",
        # Depreciação
        "deprecia":"despesas com depreciações e amortizações",
        # Totais (apenas para referência/validação, não obrigatórios)
        "lucro bruto":"lucro bruto",
        "margem bruta":"lucro bruto",
        "margem de contribuição":"lucro bruto",
        "lucro operacional":"lucro operacional",
        "ebitda":"EBITDA",
        "lucro líquido":"lucro líquido",
        "resultado líquido":"lucro líquido",
        # Não operacionais
        "rec/desp.não operacionais":"receitas não operacionais",
        # IR/CSLL
        "imposto de renda":"provisão para imposto de renda",
        "csll":"provisão para contribuição social",
        # Distribuição
        "distribuição de lucro":"pró-labore/distribuição de lucro",
        "aportes":"pró-labore/distribuição de lucro",
    }
    # Detecta automaticamente qual coluna tem o texto das contas
    # (a que tiver mais valores de texto não-numéricos)
    col_desc=df.columns[0]
    melhor_score=0
    for col in df.columns[:3]:
        try:
            vals=df[col].dropna().astype(str)
            score=sum(1 for v in vals if len(v)>3 and not v.replace(".","").replace(",","").replace("-","").isdigit())
            if score>melhor_score:
                melhor_score=score; col_desc=col
        except: pass

    # Acumula valores por (ano,mes,campo) para somar subcontas que mapeiam pro mesmo destino
    acumulado={}
    detalhamento=[]  # guarda subcontas originais para drill-down
    totais_evitar=["receita bruta de vendas","lucro bruto","lucro operacional","EBITDA",
                   "lucro líquido","CMV (custo da mercadoria vendida)"]
    # Linhas que são SUBcontas (detalhamento) somam; linhas TOTAIS (maiúsculas) não somam, usam direto
    import sys
    for _,row in df.iterrows():
        desc_raw=str(row.get(col_desc,"")).strip()
        desc=desc_raw.lower()
        if not desc or desc=="nan": continue
        campo_dest=None
        for k,v in mapa.items():
            if k in desc: campo_dest=v; break
        if "devoluç" in desc:
            print(f"DEBUG ACHEI LINHA: desc={desc!r} campo_dest={campo_dest!r}",file=sys.stderr)
        if not campo_dest: continue
        e_total=desc_raw.isupper() and len(desc_raw)>3
        for col,(ano,mes) in periodos.items():
            try:
                val=row.get(col,None)
                if val is None or str(val).strip() in ["","nan","-"]: continue
                v=float(str(val).replace(",",".").replace("%","").replace(" ",""))
                if v!=0 and abs(v)<2: continue
                chave=(ano,mes,campo_dest)
                if e_total and campo_dest in totais_evitar:
                    acumulado[chave]=abs(v)
                else:
                    acumulado[chave]=acumulado.get(chave,0)+abs(v)
                    if not e_total:
                        detalhamento.append({"ano":ano,"mes":mes,"campo_pai":campo_dest,
                                             "subconta":desc_raw,"valor":abs(v)})
            except: pass

    import sys
    n_dev=sum(1 for (a,m,c) in acumulado.keys() if c=="devoluções de vendas")
    print(f"DEBUG: chaves de devolucoes no acumulado = {n_dev}", file=sys.stderr)
    celulas=[{"ano":a,"mes":m,"campo":c,"valor":v} for (a,m,c),v in acumulado.items()]
    if detalhamento:
        celulas.append({"_detalhamento":detalhamento})
    return celulas

def parser_balanco(df, capturar_originais=False):
    periodos=extrair_periodos_colunas(df)
    if not periodos:
        if capturar_originais: return [], {}
        return []
    mapa={
        "caixa e bancos":"disponibilidades saldo",
        "caixa":"disponibilidades saldo",
        "banco":"disponibilidades saldo",
        "disponib":"disponibilidades saldo",
        "aplicaç":"disponibilidades saldo",
        "cliente":"contas a receber saldo",
        "receber":"contas a receber saldo",
        "duplicatas a receber":"contas a receber saldo",
        "estoque":"estoque final do mês de mercadorias para revenda saldo",
        "impostos a recuperar":"Outros AC",
        "tributos a recuperar":"Outros AC",
        "outros ac":"Outros AC",
        "imobilizado":"Ativo NC",
        "intangível":"Ativo NC",
        "investimentos":"Ativo NC",
        "ativo nc":"Ativo NC",
        "fornecedor":"contas a pagar de fornecedores saldo",
        "pagar a fornecedores":"contas a pagar de fornecedores saldo",
        "empréstimos cp":"Passivos Financeiros",
        "empréstimo cp":"Passivos Financeiros",
        "financiamentos cp":"Passivos Financeiros",
        "financiamento":"Passivos Financeiros",
        "salários e encargos":"Outros PC",
        "impostos a recolher":"Outros PC",
        "tributos a pagar":"Outros PC",
        "outros pc":"Outros PC",
        "empréstimos lp":"Passivo NC",
        "empréstimo lp":"Passivo NC",
        "financiamentos lp":"Passivo NC",
        "passivo nc":"Passivo NC",
        "capital social":"PL",
        "reservas":"PL",
        "lucros acumulados":"PL",
        "resultado exercício":"PL",
        "resultado do exercício":"PL",
        "ativo total":"ativo total saldo",
        "passivo total":"passivo total saldo",
    }
    col_desc=df.columns[0]
    melhor_score=0
    for col in df.columns[:3]:
        try:
            vals=df[col].dropna().astype(str)
            score=sum(1 for v in vals if len(v)>3 and not v.replace(".","").replace(",","").replace("-","").isdigit())
            if score>melhor_score:
                melhor_score=score; col_desc=col
        except: pass

    acumulado={}
    originais={}
    detalhamento=[]
    totais_evitar=["ativo total saldo","passivo total saldo"]

    for _,row in df.iterrows():
        desc_raw=str(row.get(col_desc,"")).strip()
        desc=desc_raw.lower()
        if not desc or desc=="nan": continue
        campo_dest=None
        for k,v in mapa.items():
            if k in desc: campo_dest=v; break
        if not campo_dest: continue
        e_total=desc_raw.isupper() and len(desc_raw)>3
        for col,(ano,mes) in periodos.items():
            try:
                val=row.get(col,None)
                if val is None or str(val).strip() in ["","nan","-"]: continue
                v=float(str(val).replace(",","."))
                chave=(ano,mes,campo_dest)
                if e_total and campo_dest in totais_evitar:
                    acumulado[chave]=v
                    if capturar_originais:
                        originais[chave]={"linha":desc_raw,"coluna":str(col),"valor_celula":val}
                else:
                    acumulado[chave]=acumulado.get(chave,0)+v
                    if not e_total:
                        detalhamento.append({"ano":ano,"mes":mes,"campo_pai":campo_dest,
                                             "subconta":desc_raw,"valor":v})
            except: pass

    celulas=[{"ano":a,"mes":m,"campo":c,"valor":v} for (a,m,c),v in acumulado.items()]
    if detalhamento:
        celulas.append({"_detalhamento":detalhamento})
    if capturar_originais:
        return celulas, originais
    return celulas

def parser_fluxo(df, capturar_originais=False):
    meses_pt={"jan":"jan","fev":"fev","mar":"mar","abr":"abr","mai":"mai","jun":"jun",
               "jul":"jul","ago":"ago","set":"set","out":"out","nov":"nov","dez":"dez",
               "janeiro":"jan","fevereiro":"fev","março":"mar","abril":"abr","maio":"mai",
               "junho":"jun","julho":"jul","agosto":"ago","setembro":"set",
               "outubro":"out","novembro":"nov","dezembro":"dez"}
    mapa={
        "receita serviç":"Centro de Custos Entradas 1",
        "receita produt":"Centro de Custos Entradas 2",
        "receb":"Centro de Custos Entradas 3",
        "receita financ":"Centro de Custos Entradas 4",
        "outras receitas":"Centro de Custos Entradas 4",
        "folha":"Centro de Custos Saidas 1",
        "fornecedor":"Centro de Custos Saidas 2",
        "impostos":"Centro de Custos Saidas 3",
        "desp. operac":"Centro de Custos Saidas 3",
        "despesas operac":"Centro de Custos Saidas 3",
        "investimentos":"Centro de Custos Saidas 4",
        "aluguel":"Centro de Custos Saidas 4",
        "saldo final":"disponibilidades saldo",
    }
    totais_mapa={
        "total entradas":"Disponibilidades entradas",
        "total saídas":"Disponibilidades Saida","total saidas":"Disponibilidades Saida",
    }
    # Palavras que indicam claramente ENTRADA ou SAÍDA, usadas só pra decidir o destino
    # de colunas não reconhecidas pelo mapa principal (evita perder dinheiro de vista)
    pistas_entrada=["receita","entrada","recebiment","venda","faturamento"]
    pistas_saida=["despesa","saida","saída","pagamento","custo","gasto"]

    col_ano=next((c for c in df.columns if str(c).lower() in ["ano","year"]),None)
    col_mes=next((c for c in df.columns if str(c).lower() in ["mês","mes","month"]),None)
    if not col_ano or not col_mes:
        if capturar_originais: return [], {}
        return []

    acumulado={}
    originais={}
    nao_reconhecidas=[]  # guarda {coluna, ano, mes, valor, destino} pra aviso na tela
    for _,row in df.iterrows():
        ano=str(row.get(col_ano,"")).strip()
        mes_raw=str(row.get(col_mes,"")).lower().strip()[:3]
        mes=meses_pt.get(mes_raw,mes_raw)
        if not ano or not mes or ano=="nan": continue
        for col in df.columns:
            if col in [col_ano,col_mes]: continue
            col_l=str(col).lower().strip()
            try:
                v=float(str(row.get(col,0)).replace(",","."))
            except:
                continue
            if v==0: continue
            # Verifica se é um TOTAL do arquivo (usa direto, não soma) — só para auditoria/referência
            campo_total=None
            for k,dest in totais_mapa.items():
                if k in col_l: campo_total=dest; break
            if campo_total:
                chave=(ano,mes,campo_total)
                if capturar_originais:
                    originais[chave]={"linha":col_l,"coluna":str(col),"valor_celula":v}
                continue
            # Senão, é uma categoria — soma no campo de destino
            campo_dest=None
            for k,dest in mapa.items():
                if k in col_l: campo_dest=dest; break
            if not campo_dest:
                # Coluna não reconhecida — NUNCA descarta o dinheiro.
                # Decide se é Entrada ou Saída por pista textual; se não achar pista, assume Entrada
                # quando valor positivo (mais comum) e avisa para revisão.
                eh_saida=any(p in col_l for p in pistas_saida)
                campo_dest="Centro de Custos Saidas 4" if eh_saida else "Centro de Custos Entradas 4"
                nao_reconhecidas.append({"coluna":str(col),"ano":ano,"mes":mes,
                                         "valor":v,"destino":"Saída" if eh_saida else "Entrada"})
            chave=(ano,mes,campo_dest)
            acumulado[chave]=acumulado.get(chave,0)+v

    # Calcula os totais (Disponibilidades entradas/Saida) somando as categorias mapeadas
    totais_calculados={}
    campos_entrada=["Centro de Custos Entradas 1","Centro de Custos Entradas 2",
                    "Centro de Custos Entradas 3","Centro de Custos Entradas 4"]
    campos_saida=["Centro de Custos Saidas 1","Centro de Custos Saidas 2",
                  "Centro de Custos Saidas 3","Centro de Custos Saidas 4"]
    periodos_vistos=set((a,m) for (a,m,c) in acumulado.keys())
    for (ano,mes) in periodos_vistos:
        soma_ent=sum(acumulado.get((ano,mes,c),0) for c in campos_entrada)
        soma_sai=sum(acumulado.get((ano,mes,c),0) for c in campos_saida)
        totais_calculados[(ano,mes,"Disponibilidades entradas")]=soma_ent
        totais_calculados[(ano,mes,"Disponibilidades Saida")]=soma_sai

    # Detalhamento para drill-down: cada categoria mapeada vira subconta do campo consolidado
    nomes_legiveis={
        "Centro de Custos Entradas 1":"Receita Serviços","Centro de Custos Entradas 2":"Receita Produtos",
        "Centro de Custos Entradas 3":"Recebimento Clientes","Centro de Custos Entradas 4":"Receita Financeira/Outras",
        "Centro de Custos Saidas 1":"Folha","Centro de Custos Saidas 2":"Fornecedores",
        "Centro de Custos Saidas 3":"Impostos/Operacionais","Centro de Custos Saidas 4":"Investimentos",
    }
    detalhamento=[]
    for (ano,mes,campo),valor in acumulado.items():
        if campo in campos_entrada:
            detalhamento.append({"ano":ano,"mes":mes,"campo_pai":"Disponibilidades entradas",
                                 "subconta":nomes_legiveis.get(campo,campo),"valor":valor})
        elif campo in campos_saida:
            detalhamento.append({"ano":ano,"mes":mes,"campo_pai":"Disponibilidades Saida",
                                 "subconta":nomes_legiveis.get(campo,campo),"valor":valor})

    celulas=[{"ano":a,"mes":m,"campo":c,"valor":v} for (a,m,c),v in acumulado.items()]
    celulas+=[{"ano":a,"mes":m,"campo":c,"valor":v} for (a,m,c),v in totais_calculados.items()]
    if detalhamento:
        celulas.append({"_detalhamento":detalhamento})
    if nao_reconhecidas:
        celulas.append({"_nao_reconhecidas":nao_reconhecidas})
    if capturar_originais:
        return celulas, originais
    return celulas

def mapear_celulas_brutas(celulas_brutas, tipo):
    """Recebe células BRUTAS no formato {ano, mes, conta(texto original), valor}
    e aplica o motor de regras determinístico (mesmo mapa do parser_dre/balanco)
    para somar subcontas no campo de destino padrão do sistema.
    Isso garante que a soma de subcontas SEMPRE seja feita por regra, nunca por IA."""

    if tipo=="DRE":
        mapa={
            "receita bruta":"receita bruta de vendas","faturamento":"receita bruta de vendas",
            "receita da venda":"receita bruta de vendas","receita de vendas":"receita bruta de vendas",
            "receita de serviços":"receita bruta de vendas","receita de serviço":"receita bruta de vendas",
            "serviços recorrentes":"receita bruta de vendas","serviços avulsos":"receita bruta de vendas",
            "venda de mercadorias":"receita bruta de vendas","vendas brutas":"receita bruta de vendas",
            "receita total":"receita bruta de vendas","outras receitas operacionais":"receita bruta de vendas",
            "imposto sobre vendas":"impostos sobre vendas","imposto":"impostos sobre vendas",
            "deduç":"impostos sobre vendas",
            "devoluç":"devoluções de vendas","abatimento":"devoluções de vendas",
            "desconto concedido":"devoluções de vendas","descontos concedidos":"devoluções de vendas",
            "cmv":"CMV (custo da mercadoria vendida)","custo da mercadoria":"CMV (custo da mercadoria vendida)",
            "custo dos serviços":"CMV (custo da mercadoria vendida)","custo do produto":"CMV (custo da mercadoria vendida)",
            "custo variável":"CMV (custo da mercadoria vendida)","insumos":"CMV (custo da mercadoria vendida)",
            "embalagem":"CMV (custo da mercadoria vendida)","frete":"CMV (custo da mercadoria vendida)",
            "mão de obra direta":"CMV (custo da mercadoria vendida)","materiais e insumos":"CMV (custo da mercadoria vendida)",
            "fretes de produção":"CMV (custo da mercadoria vendida)",
            "despesas comerciais":"despesas comerciais","desp comerci":"despesas comerciais",
            "brindes":"despesas comerciais","feiras e eventos":"despesas comerciais","marketing":"despesas comerciais",
            "salários comerciais":"despesas comerciais","comissões":"despesas comerciais",
            "viagens comerciais":"despesas comerciais","marketing e publicidade":"despesas comerciais",
            "despesas com pessoal":"despesas administrativas","salários":"despesas administrativas",
            "encargos":"despesas administrativas","benefícios":"despesas administrativas",
            "aluguel":"despesas administrativas","manutenção":"despesas administrativas",
            "despesas administrativas":"despesas administrativas","serviços adm":"despesas administrativas",
            "salários administrativos":"despesas administrativas","pró-labore":"despesas administrativas",
            "energia elétrica":"despesas administrativas","internet e telefonia":"despesas administrativas",
            "contabilidade":"despesas administrativas","sistemas e licenças":"despesas administrativas",
            "material de escritório":"despesas administrativas","seguros":"despesas administrativas",
            "treinamentos":"despesas administrativas","desp admin":"despesas administrativas",
            "desp financ":"despesas financeiras líquidas","juros pagos":"despesas financeiras líquidas",
            "despesas financeiras":"despesas financeiras líquidas","juros bancários":"despesas financeiras líquidas",
            "tarifas bancárias":"despesas financeiras líquidas",
            "juros recebidos":"receitas não operacionais","receitas financeiras":"receitas não operacionais",
            "juros ativos":"receitas não operacionais",
            "deprecia":"despesas com depreciações e amortizações",
            "imposto de renda":"provisão para imposto de renda","irpj":"provisão para imposto de renda",
            "csll":"provisão para contribuição social",
            "distribuição de lucro":"pró-labore/distribuição de lucro",
        }
    elif tipo=="BALANCO":
        mapa={
            "caixa":"disponibilidades saldo","banco":"disponibilidades saldo",
            "disponib":"disponibilidades saldo","aplicaç":"disponibilidades saldo",
            "caixa e bancos":"disponibilidades saldo",
            "cliente":"contas a receber saldo","receber":"contas a receber saldo",
            "estoque":"estoque final do mês de mercadorias para revenda saldo",
            "impostos a recuperar":"Outros AC","tributos a recuperar":"Outros AC","outros ac":"Outros AC",
            "imobilizado":"Ativo NC","intangível":"Ativo NC","investimentos":"Ativo NC","ativo nc":"Ativo NC",
            "fornecedor":"contas a pagar de fornecedores saldo",
            "empréstimos cp":"Passivos Financeiros","empréstimo cp":"Passivos Financeiros",
            "financiamentos cp":"Passivos Financeiros","financiamento":"Passivos Financeiros",
            "salários e encargos":"Outros PC","impostos a recolher":"Outros PC","outros pc":"Outros PC",
            "empréstimos lp":"Passivo NC","empréstimo lp":"Passivo NC",
            "financiamentos lp":"Passivo NC","passivo nc":"Passivo NC",
            "capital social":"PL","reservas":"PL","lucros acumulados":"PL",
            "resultado exercício":"PL","resultado do exercício":"PL",
            "ativo total":"ativo total saldo","passivo total":"passivo total saldo",
        }
    elif tipo=="FLUXO":
        mapa={
            "total entradas":"Disponibilidades entradas",
            "receita serviç":"Centro de Custos Entradas 1","receita produt":"Centro de Custos Entradas 2",
            "receb":"Centro de Custos Entradas 3","outras receitas":"Centro de Custos Entradas 4",
            "total saídas":"Disponibilidades Saida","total saidas":"Disponibilidades Saida",
            "folha":"Centro de Custos Saidas 1","fornecedor":"Centro de Custos Saidas 2",
            "aluguel":"Centro de Custos Saidas 3","desp. operac":"Centro de Custos Saidas 4",
            "saldo final":"disponibilidades saldo",
        }
    else:
        return []

    meses_pt={"jan":"jan","fev":"fev","mar":"mar","abr":"abr","mai":"mai","jun":"jun",
               "jul":"jul","ago":"ago","set":"set","out":"out","nov":"nov","dez":"dez",
               "janeiro":"jan","fevereiro":"fev","março":"mar","abril":"abr","maio":"mai",
               "junho":"jun","julho":"jul","agosto":"ago","setembro":"set",
               "outubro":"out","novembro":"nov","dezembro":"dez"}

    acumulado={}
    for c in celulas_brutas:
        conta_raw=str(c.get("conta","")).strip()
        conta=conta_raw.lower()
        mes_raw=str(c.get("mes","")).lower().strip()[:3]
        mes=meses_pt.get(mes_raw,mes_raw)
        ano=str(c.get("ano",""))
        if not conta or not mes or not ano: continue
        campo_dest=None
        for k,v in mapa.items():
            if k in conta: campo_dest=v; break
        if not campo_dest: continue
        try:
            v=abs(float(c.get("valor",0)))
            chave=(ano,mes,campo_dest)
            acumulado[chave]=acumulado.get(chave,0)+v
        except: pass

    return [{"ano":a,"mes":m,"campo":cp,"valor":v} for (a,m,cp),v in acumulado.items()]



    prompt=f"""Você é um extrator de dados financeiros. NÃO interprete, NÃO some, NÃO mapeie nada —
apenas extraia cada linha de dado bruto exatamente como está no arquivo.

TIPO DO DOCUMENTO: {tipo}

ARQUIVO:
{amostra}

INSTRUÇÕES:
1. Para cada valor numérico no arquivo, identifique: ANO, MÊS, nome da CONTA (exatamente como
   escrito no arquivo, sem traduzir ou simplificar) e o VALOR
2. Ignore linhas de total/subtotal SE houver linhas de detalhe que já somam ao mesmo resultado
   (evite duplicar). Se não tiver certeza, inclua a linha mesmo assim.
3. Ignore colunas de %, médias, ou texto sem valor numérico
4. Mantenha valores negativos como estão (não inverta sinais)
5. mês deve ser um dos: jan/fev/mar/abr/mai/jun/jul/ago/set/out/nov/dez (ou nome completo)

Retorne SOMENTE este JSON, sem texto adicional, sem markdown:
{{"celulas":[{{"ano":"2024","mes":"jan","conta":"Receita de Vendas","valor":552000}}]}}"""
    try:
        txt=""
        if not api_key.startswith("sk-ant-") and OPENAI_OK:
            client=OpenAI(api_key=api_key)
            r=client.chat.completions.create(model="gpt-4o",max_tokens=32000,
              messages=[{"role":"system","content":"Você é um extrator literal de dados. Retorne APENAS JSON válido sem markdown."},
                        {"role":"user","content":prompt}])
            txt=r.choices[0].message.content.strip()
        elif ANTHROPIC_OK:
            client=anthropic.Anthropic(api_key=api_key)
            r=client.messages.create(model="claude-sonnet-4-6",max_tokens=32000,
              system="Você é um extrator literal de dados. Retorne APENAS JSON válido sem markdown.",
              messages=[{"role":"user","content":prompt}])
            txt=r.content[0].text.strip()
        txt=re.sub(r'^```json\s*','',txt); txt=re.sub(r'\s*```$','',txt)
        return json.loads(txt).get("celulas",[])
    except Exception as e:
        return []

def _chamar_ia_extracao_bruta_lote(df_cli, api_key, tipo):
    amostra=df_cli.to_string(max_cols=df_cli.shape[1])
    prompt=f"""Você é um extrator de dados financeiros. NÃO interprete, NÃO some, NÃO mapeie nada —
apenas extraia cada linha de dado bruto exatamente como está no arquivo.

TIPO DO DOCUMENTO: {tipo}

ARQUIVO:
{amostra}

INSTRUÇÕES:
1. Para cada valor numérico no arquivo, identifique: ANO, MÊS, nome da CONTA (exatamente como
   escrito no arquivo, sem traduzir ou simplificar) e o VALOR
2. Ignore linhas de total/subtotal SE houver linhas de detalhe que já somam ao mesmo resultado
   (evite duplicar). Se não tiver certeza, inclua a linha mesmo assim.
3. Ignore colunas de %, médias, ou texto sem valor numérico
4. Mantenha valores negativos como estão (não inverta sinais)
5. mês deve ser um dos: jan/fev/mar/abr/mai/jun/jul/ago/set/out/nov/dez (ou nome completo)
6. Extraia TODOS os registros do arquivo, não pare antes do final

Retorne SOMENTE este JSON, sem texto adicional, sem markdown:
{{"celulas":[{{"ano":"2024","mes":"jan","conta":"Receita de Vendas","valor":552000}}]}}"""
    try:
        txt=""
        if not api_key.startswith("sk-ant-") and OPENAI_OK:
            client=OpenAI(api_key=api_key)
            r=client.chat.completions.create(model="gpt-4o",max_tokens=32000,
              messages=[{"role":"system","content":"Você é um extrator literal de dados. Retorne APENAS JSON válido sem markdown."},
                        {"role":"user","content":prompt}])
            txt=r.choices[0].message.content.strip()
        elif ANTHROPIC_OK:
            client=anthropic.Anthropic(api_key=api_key)
            r=client.messages.create(model="claude-sonnet-4-6",max_tokens=32000,
              system="Você é um extrator literal de dados. Retorne APENAS JSON válido sem markdown.",
              messages=[{"role":"user","content":prompt}])
            txt=r.content[0].text.strip()
        txt=re.sub(r'^```json\s*','',txt); txt=re.sub(r'\s*```$','',txt)
        return json.loads(txt).get("celulas",[])
    except Exception as e:
        import sys
        print(f"ERRO em _chamar_ia_extracao_bruta_lote: {e}", file=sys.stderr)
        return []

def _chamar_ia_extracao_bruta(df_cli, api_key, tipo):
    col_ano_bruta=None
    for col in df_cli.columns[:3]:
        if str(col).lower().strip() in ["ano","year"]:
            col_ano_bruta=col; break
    if col_ano_bruta is None or df_cli.shape[0]<=300:
        n_linhas=min(len(df_cli),300)
        return _chamar_ia_extracao_bruta_lote(df_cli.head(n_linhas),api_key,tipo)
    todas_celulas=[]
    anos_unicos=df_cli[col_ano_bruta].dropna().unique()
    for ano_lote in anos_unicos:
        df_lote=df_cli[df_cli[col_ano_bruta]==ano_lote]
        celulas_lote=_chamar_ia_extracao_bruta_lote(df_lote,api_key,tipo)
        todas_celulas.extend(celulas_lote)
    return todas_celulas

def _chamar_ia_extracao(df_cli, campos, api_key, tipo):
    amostra=df_cli.head(60).to_string(max_cols=df_cli.shape[1])
    prompt=f"""Você é um especialista em contabilidade brasileira analisando uma demonstração financeira.

TIPO PROVÁVEL: {tipo} (pode ser DRE, Balanço Patrimonial ou Fluxo de Caixa — confirme pelo conteúdo)

ARQUIVO (pode ter qualquer layout — vertical, horizontal, com subcontas, com totais em destaque):
{amostra}

CAMPOS PADRÃO DO SISTEMA (mapeie os termos do arquivo para estes, mesmo que os nomes sejam diferentes,
sinônimos, abreviações, plural/singular, ou em outro idioma):
{json.dumps(campos,ensure_ascii=False)}

REGRAS IMPORTANTES:
1. Identifique ANO e MÊS de cada valor (mês: jan/fev/mar/abr/mai/jun/jul/ago/set/out/nov/dez)
2. Se o arquivo tem SUBCONTAS detalhadas que pertencem a uma conta principal (ex: "Insumos",
   "Embalagem", "Frete" todos compondo o CMV), SOME essas subcontas no campo de destino correto
3. Se o arquivo já tem TOTAIS calculados (ex: "RECEITA BRUTA" em destaque/maiúsculo), use esse
   valor direto em vez de tentar somar subcontas, para não duplicar
4. Ignore colunas de %AV (análise vertical), %AH (análise horizontal), médias, ou variações percentuais
5. Valores devem ser sempre positivos (remova sinais negativos de despesas/deduções)
6. Se o arquivo for horizontal (meses como colunas), extraia corretamente cada coluna-mês
7. Se o arquivo for vertical (meses como linhas), extraia corretamente cada linha-mês
8. O ANO pode estar implícito no título/cabeçalho da planilha (ex: "DRE 2024") — use-o para todos os meses
9. Tente mapear o MÁXIMO de contas possível, mesmo termos não óbvios — use seu conhecimento contábil
10. Reconheça variações comuns: "Faturamento"="Receita Bruta", "Custo da Mercadoria Vendida"="CMV",
    "Despesas com Pessoal"="Despesas Administrativas", "Resultado Líquido"="Lucro Líquido", etc.

Retorne SOMENTE este JSON, sem texto adicional, sem markdown:
{{"celulas":[{{"ano":"2024","mes":"jan","campo":"receita bruta de vendas","valor":1234567.89}}]}}"""
    try:
        txt=""
        if not api_key.startswith("sk-ant-") and OPENAI_OK:
            client=OpenAI(api_key=api_key)
            r=client.chat.completions.create(model="gpt-4o",max_tokens=16000,
              messages=[{"role":"system","content":"Você é um especialista contábil. Retorne APENAS JSON válido sem markdown."},
                        {"role":"user","content":prompt}])
            txt=r.choices[0].message.content.strip()
        elif ANTHROPIC_OK:
            client=anthropic.Anthropic(api_key=api_key)
            r=client.messages.create(model="claude-sonnet-4-6",max_tokens=16000,
              system="Você é um especialista contábil. Retorne APENAS JSON válido sem markdown.",
              messages=[{"role":"user","content":prompt}])
            txt=r.content[0].text.strip()
        txt=re.sub(r'^```json\s*','',txt); txt=re.sub(r'\s*```$','',txt)
        return json.loads(txt).get("celulas",[])
    except Exception as e:
        return []

def ia_extrair(df_cli, campos, api_key):
    tipo=detectar_tipo(df_cli)
    celulas_local=[]
    if tipo=="DRE": celulas_local=parser_dre(df_cli)
    elif tipo=="BALANCO": celulas_local=parser_balanco(df_cli)
    elif tipo=="FLUXO": celulas_local=parser_fluxo(df_cli)
    if len(celulas_local)>=10:
        return celulas_local
    if not api_key: return celulas_local
    amostra=df_cli.head(50).to_string(max_cols=30)
    prompt=f"""Especialista contabilidade brasileira. Analise o arquivo e extraia dados financeiros.

TIPO DETECTADO: {tipo}

ARQUIVO:
{amostra}

CAMPOS NECESSÁRIOS:
{json.dumps(campos[:30],ensure_ascii=False)}

REGRAS:
1. ANO e MÊS de cada valor (mês: jan/fev/mar/abr/mai/jun/jul/ago/set/out/nov/dez)
2. Ignore totais acumulados, %AV, %AH, médias
3. Valores reais — não percentuais
4. Se horizontal (meses nas colunas), gire corretamente
5. ANO pode estar no nome da coluna

Retorne SOMENTE JSON:
{{"celulas":[{{"ano":"2024","mes":"jan","campo":"receita bruta de vendas","valor":1234567.89}}]}}"""
    try:
        txt=""
        if not api_key.startswith("sk-ant-") and OPENAI_OK:
            client=OpenAI(api_key=api_key)
            r=client.chat.completions.create(model="gpt-4o",max_tokens=16000,
              messages=[{"role":"system","content":"Retorne APENAS JSON válido sem markdown."},
                        {"role":"user","content":prompt}])
            txt=r.choices[0].message.content.strip()
        elif ANTHROPIC_OK:
            client=anthropic.Anthropic(api_key=api_key)
            r=client.messages.create(model="claude-sonnet-4-6",max_tokens=16000,
              system="Retorne APENAS JSON válido sem markdown.",
              messages=[{"role":"user","content":prompt}])
            txt=r.content[0].text.strip()
        txt=re.sub(r'^```json\s*','',txt); txt=re.sub(r'\s*```$','',txt)
        celulas_ia=json.loads(txt).get("celulas",[])
        chaves_local={(c["ano"],c["mes"],c["campo"]) for c in celulas_local}
        for c in celulas_ia:
            if (c.get("ano"),c.get("mes"),c.get("campo")) not in chaves_local:
                celulas_local.append(c)
        return celulas_local
    except Exception as e:
        st.error(f"Erro IA: {e}"); return celulas_local

def celulas_to_df(celulas):
    reg={}
    for c in celulas:
        k=(str(c.get("ano","")),str(c.get("mes","")).lower()[:3])
        if k not in reg: reg[k]={"Ano":k[0],"mês":k[1]}
        try:
            reg[k][c["campo"]]=float(c["valor"])
        except:
            reg[k][c["campo"]]=c["valor"]
    if not reg: return pd.DataFrame()
    df=pd.DataFrame(list(reg.values()))
    # Garante TODOS os campos de TODAS as demonstrações, mesmo que não tenham vindo neste arquivo
    todos_campos=set()
    for r in reg.values(): todos_campos.update(r.keys())
    todos_campos.update(TODOS)  # garante cobertura total do padrão do sistema
    for campo in todos_campos:
        if campo in ["Ano","mês"]: continue
        if campo not in df.columns: df[campo]=0.
        else: df[campo]=df[campo].fillna(0.)
    try:
        df["Data"]=pd.to_datetime(
            df["Ano"].astype(str)+"-"+
            df["mês"].astype(str).str.lower().str[:3].map(MES_NUM).fillna("01")+"-01",
            errors="coerce")
        df=df.sort_values("Data").reset_index(drop=True)
    except: pass
    return df

def identificar_demonstracao(celulas):
    if not celulas: return None
    campos_presentes={c["campo"] for c in celulas}
    melhor_demo=None; melhor_score=0
    for nome_demo,campos_demo in DEMONSTRACOES_CAMPOS.items():
        score=len(campos_presentes & set(campos_demo))
        if score>melhor_score:
            melhor_score=score; melhor_demo=nome_demo
    return melhor_demo

def merge_banco_por_demonstracao(df_existente, celulas_novas, nome_demo):
    df_novo=celulas_to_df(celulas_novas)
    if df_novo.empty: return df_existente
    campos_desta_demo=DEMONSTRACOES_CAMPOS.get(nome_demo,[])
    if df_existente is None or df_existente.empty:
        for outra_demo,campos in DEMONSTRACOES_CAMPOS.items():
            if outra_demo==nome_demo: continue
            for c in campos:
                if c not in df_novo.columns: df_novo[c]=0.
        return df_novo
    df_existente=df_existente.copy()
    if "Ano" not in df_existente.columns or "mês" not in df_existente.columns:
        return df_novo
    df_existente["_chave"]=df_existente["Ano"].astype(str)+"_"+df_existente["mês"].astype(str).str.lower().str[:3]
    df_novo["_chave"]=df_novo["Ano"].astype(str)+"_"+df_novo["mês"].astype(str).str.lower().str[:3]
    cols_remover=[c for c in campos_desta_demo if c in df_existente.columns]
    df_existente_limpo=df_existente.drop(columns=cols_remover,errors="ignore")
    chaves_existentes=set(df_existente_limpo["_chave"])
    chaves_novas=set(df_novo["_chave"])
    todas_chaves=chaves_existentes | chaves_novas
    linhas_final=[]
    for chave in sorted(todas_chaves):
        linha={}
        row_exist=df_existente_limpo[df_existente_limpo["_chave"]==chave]
        if len(row_exist)>0:
            linha.update(row_exist.iloc[0].to_dict())
        else:
            ano,mes=chave.split("_",1)
            linha={"Ano":ano,"mês":mes}
        row_novo=df_novo[df_novo["_chave"]==chave]
        if len(row_novo)>0:
            for c in campos_desta_demo:
                if c in row_novo.columns:
                    linha[c]=float(row_novo.iloc[0].get(c,0) or 0)
        for c in campos_desta_demo:
            if c not in linha: linha[c]=0.
        linhas_final.append(linha)
    df_final=pd.DataFrame(linhas_final)
    df_final=df_final.drop(columns=["_chave"],errors="ignore")
    for nome_demo2,campos2 in DEMONSTRACOES_CAMPOS.items():
        for c in campos2:
            if c not in df_final.columns: df_final[c]=0.
            else: df_final[c]=df_final[c].fillna(0.)
    try:
        df_final["Data"]=pd.to_datetime(
            df_final["Ano"].astype(str)+"-"+
            df_final["mês"].astype(str).str.lower().str[:3].map(MES_NUM).fillna("01")+"-01",
            errors="coerce")
        df_final=df_final.sort_values("Data").reset_index(drop=True)
    except: pass
    return df_final

def gerar_cobertura(df, demonstracoes_campos):
    if df.empty: return pd.DataFrame()
    cm=cm_(df); ca=ca_(df)
    linhas=[]
    for _,row in df.iterrows():
        linha={"Ano":row.get(ca,""),"Mês":row.get(cm,"")}
        for nome_demo,campos_demo in demonstracoes_campos.items():
            preenchidos=sum(1 for c in campos_demo if c in df.columns and float(row.get(c,0) or 0)!=0)
            total=len(campos_demo)
            linha[nome_demo]="✅" if preenchidos>0 else "⚪"
            linha[f"{nome_demo}_qtd"]=f"{preenchidos}/{total}"
        linhas.append(linha)
    return pd.DataFrame(linhas)

# ═══════════════════════════════════════════════════
# CÁLCULOS
# ═══════════════════════════════════════════════════
def calcular(df):
    d=df.copy()
    d["deduções"]         = cn(d,"impostos sobre vendas")+cn(d,"devoluções de vendas")
    d["receita líquida"]  = cn(d,"receita bruta de vendas")-d["deduções"]
    d["lucro bruto"]      = d["receita líquida"]-cn(d,"CMV (custo da mercadoria vendida)")
    d["margem contrib"]   = d["lucro bruto"]-cn(d,"despesas comerciais")
    d["desp op"]          = (cn(d,"despesas comerciais")+cn(d,"despesas administrativas")+
                             cn(d,"despesas financeiras líquidas")+cn(d,"despesas com depreciações e amortizações"))
    d["lucro operacional"]= d["lucro bruto"]-d["desp op"]
    d["resultado IR"]     = d["lucro operacional"]+cn(d,"receitas não operacionais")-cn(d,"despesas não operacionais")
    d["lucro líquido"]    = d["resultado IR"]-cn(d,"provisão para imposto de renda")-cn(d,"provisão para contribuição social")
    d["EBITDA"]           = (d["lucro líquido"]+cn(d,"provisão para imposto de renda")+
                             cn(d,"provisão para contribuição social")+
                             cn(d,"despesas financeiras líquidas")+
                             cn(d,"despesas com depreciações e amortizações"))
    rl=d["receita líquida"].replace(0,np.nan)
    d["margem bruta %"]   = d["lucro bruto"]/rl*100
    d["margem contrib %"] = d["margem contrib"]/rl*100
    d["margem op %"]      = d["lucro operacional"]/rl*100
    d["margem líquida %"] = d["lucro líquido"]/rl*100
    d["EBITDA %"]         = d["EBITDA"]/rl*100
    d["ativo circ"]       = (cn(d,"disponibilidades saldo")+cn(d,"contas a receber saldo")+
                             cn(d,"estoque final do mês de mercadorias para revenda saldo")+cn(d,"Outros AC"))
    d["ativo total"]      = d["ativo circ"]+cn(d,"Ativo NC")
    d["pass circ"]        = (cn(d,"contas a pagar de fornecedores saldo")+cn(d,"Passivos Financeiros")+cn(d,"Outros PC"))
    d["pass total"]       = d["pass circ"]+cn(d,"Passivo NC")
    d["PL"]               = d["ativo total"]-d["pass total"]
    pc=d["pass circ"].replace(0,np.nan); pt=d["pass total"].replace(0,np.nan)
    pl=d["PL"].replace(0,np.nan);       at=d["ativo total"].replace(0,np.nan)
    ac=d["ativo circ"]
    est=cn(d,"estoque final do mês de mercadorias para revenda saldo")
    ei =cn(d,"estoque inicial do mês de mercadorias para revenda saldo")
    cmv=cn(d,"CMV (custo da mercadoria vendida)")
    cr =cn(d,"contas a receber saldo"); cp=cn(d,"contas a pagar de fornecedores saldo")
    d["liquidez corrente"] = ac/pc
    d["liquidez imediata"] = cn(d,"disponibilidades saldo")/pc
    d["ROE"]    = d["lucro líquido"]/pl*100
    d["kanitz"] = (0.05*(d["lucro líquido"]/pl.fillna(1))+
                   1.65*(at.fillna(0)/pt.fillna(1))+
                   3.55*((ac-est)/pc.fillna(1))+
                   1.06*(ac/pc.fillna(1))+
                   0.33*(pt.fillna(0)/pl.fillna(1)))
    d["PMR"]  = (cr/(rl.fillna(1)*12))*365
    compras   = (est+cmv-ei)*12
    d["PMP"]  = (cp/compras.replace(0,np.nan).fillna(1))*365
    giro      = cmv/((ei+est)/2).replace(0,np.nan)
    d["PME"]  = 30/giro.replace(0,np.nan)
    d["ciclo de caixa"] = d["PMR"]+d["PME"]-d["PMP"]
    d["giro estoque"]   = giro
    d["ticket médio"]   = rl/cn(d,"numero de vendas").replace(0,np.nan)
    pf=cn(d,"Passivos Financeiros"); disp=cn(d,"disponibilidades saldo")
    d["ICD"]  = d["EBITDA"]/(pf-disp).replace(0,np.nan)*100
    ent=cn(d,"Disponibilidades entradas"); sai=cn(d,"Disponibilidades Saida")
    d["saldo período"]   = ent-sai
    d["saldo acumulado"] = d["saldo período"].cumsum()
    scores=[]
    for _,row in d.iterrows():
        try:
            k=float(row.get("kanitz",0) or 0)
            k_norm=max(0,min(1,(k-(-4))/(0-(-4))))
            li=float(row.get("liquidez imediata",0) or 0)*100
            li_norm=max(0,min(1,li/5))
            eb=float(row.get("EBITDA %",0) or 0)
            eb_norm=max(0,min(1,eb/5)) if eb>0 else 0
            cc=float(row.get("ciclo de caixa",0) or 0)
            cc_norm=max(0,min(1,(120-cc)/120))
            s=(k_norm*0.25+li_norm*0.25+eb_norm*0.25+cc_norm*0.25)*100
        except: s=0.
        scores.append(round(max(0,min(100,s)),2))
    d["score_risco"]=scores
    d["ativo circ"]  = (cn(d,"disponibilidades saldo")+cn(d,"contas a receber saldo")+
                        cn(d,"estoque final do mês de mercadorias para revenda saldo")+cn(d,"Outros AC"))
    d["ativo total"] = d["ativo circ"]+cn(d,"Ativo NC")
    d["pass circ"]   = (cn(d,"contas a pagar de fornecedores saldo")+cn(d,"Passivos Financeiros")+cn(d,"Outros PC"))
    d["pass total"]  = d["pass circ"]+cn(d,"Passivo NC")
    d["PL"]          = d["ativo total"]-d["pass total"]
    pc=d["pass circ"].replace(0,np.nan); pt=d["pass total"].replace(0,np.nan)
    pl=d["PL"].replace(0,np.nan);       at=d["ativo total"].replace(0,np.nan)
    ac=d["ativo circ"]
    est=cn(d,"estoque final do mês de mercadorias para revenda saldo")
    ei =cn(d,"estoque inicial do mês de mercadorias para revenda saldo")
    cmv=cn(d,"CMV (custo da mercadoria vendida)")
    cr =cn(d,"contas a receber saldo"); cp=cn(d,"contas a pagar de fornecedores saldo")
    d["liquidez corrente"] = ac/pc
    d["liquidez imediata"] = cn(d,"disponibilidades saldo")/pc
    d["ROE"]    = d["lucro líquido"]/pl*100
    d["kanitz"] = (0.05*(d["lucro líquido"]/pl.fillna(1))+1.65*(at.fillna(0)/pt.fillna(1))+
                   3.55*((ac-est)/pc.fillna(1))-1.06*(ac/pc.fillna(1))-0.33*(pt.fillna(0)/pl.fillna(1)))
    d["PMR"] = (cr/(rl.fillna(1)*12))*365
    compras  = (est+cmv-ei)*12
    d["PMP"] = (cp/compras.replace(0,np.nan).fillna(1))*365
    giro     = cmv/((ei+est)/2).replace(0,np.nan)
    d["PME"] = 30/giro.replace(0,np.nan)
    d["ciclo de caixa"] = d["PMR"]+d["PME"]-d["PMP"]
    d["giro estoque"]   = giro
    d["ticket médio"]   = rl/cn(d,"numero de vendas").replace(0,np.nan)
    pf=cn(d,"Passivos Financeiros"); disp=cn(d,"disponibilidades saldo")
    d["ICD"] = d["EBITDA"]/(pf-disp).replace(0,np.nan)*100
    ent=cn(d,"Disponibilidades entradas"); sai=cn(d,"Disponibilidades Saida")
    d["saldo período"]   = ent-sai
    d["saldo acumulado"] = d["saldo período"].cumsum()
    scores=[]
    for _,row in d.iterrows():
        try:
            k=float(row.get("kanitz",0) or 0)
            k_norm=max(0,min(1,(k-(-4))/(0-(-4))))
            li=float(row.get("liquidez imediata",0) or 0)*100
            li_norm=max(0,min(1,li/5))
            eb=float(row.get("EBITDA %",0) or 0)
            eb_norm=max(0,min(1,eb/5)) if eb>0 else 0
            cc=float(row.get("ciclo de caixa",0) or 0)
            cc_norm=max(0,min(1,(120-cc)/120))
            s=(k_norm*0.25+li_norm*0.25+eb_norm*0.25+cc_norm*0.25)*100
        except: s=0.
        scores.append(round(max(0,min(100,s)),2))
    d["score_risco"]=scores
    return d

def score_label(s):
    try:
        v=float(s)
        if v>=80: return "🟢 Baixo Risco","g","#059669"
        if v>=60: return "🟡 Risco Moderado","y","#D97706"
        if v>=40: return "🟠 Alto Risco","y","#EA580C"
        if v>=20: return "🔴 Risco Crítico","r","#DC2626"
        return "⚫ Insolvência Iminente","r","#6B7280"
    except: return "—","","#6B7280"

def detectar_anomalias(serie,janela=3,mult=1.3):
    s=pd.to_numeric(serie,errors="coerce").fillna(0)
    if len(s)<4: return pd.Series([False]*len(s),index=s.index)
    mm=s.rolling(janela,center=True,min_periods=1).mean()
    std=s.rolling(janela,center=True,min_periods=1).std().fillna(1)
    return (s-mm).abs()>mult*std

# ═══════════════════════════════════════════════════
# ML
# ═══════════════════════════════════════════════════
def treinar(serie,modelo,n=6):
    try:
        s=pd.to_numeric(serie,errors="coerce").dropna()
        if len(s)<6: return None
        if modelo=="ARIMA" and STATS_OK:
            return ARIMA(s,order=(3,1,1)).fit().forecast(n)
        if modelo=="SARIMAX" and STATS_OK and len(s)>=24:
            return SARIMAX(s,order=(1,1,1),seasonal_order=(1,1,1,12)).fit(disp=False).forecast(n)
        if modelo=="ExponentialSmoothing" and STATS_OK:
            kw={"trend":"add","damped_trend":True}
            if len(s)>=24: kw.update({"seasonal":"add","seasonal_periods":12})
            return ExponentialSmoothing(s,**kw).fit().forecast(n)
        if modelo=="Holt" and STATS_OK:
            return Holt(s,damped_trend=True).fit().forecast(n)
        if modelo=="Média Móvel":
            mm=s.rolling(3).mean().iloc[-1]; return pd.Series([mm]*n)
        if modelo=="Prophet" and PROPHET_OK:
            idx=pd.date_range(end=pd.Timestamp.now(),periods=len(s),freq="MS")
            df_p=pd.DataFrame({"ds":idx,"y":s.values})
            m=Prophet(changepoint_prior_scale=0.01,yearly_seasonality=True); m.fit(df_p)
            fut=m.make_future_dataframe(periods=n,freq="MS"); fc=m.predict(fut)
            return pd.Series(fc["yhat"].tail(n).values)
    except: pass
    return None

def mse_modelo(serie,modelo):
    try:
        s=pd.to_numeric(serie,errors="coerce").dropna()
        if len(s)<14: return float("inf")
        tr,te=s.iloc[:-6],s.iloc[-6:]
        pr=treinar(tr,modelo,6)
        if pr is None: return float("inf")
        return float(mean_squared_error(te.values,pr.values[:6]))
    except: return float("inf")

def melhor_modelo(serie,modelos):
    res={m:mse_modelo(serie,m) for m in modelos}
    res={k:v for k,v in res.items() if v<float("inf")}
    if not res: return "Média Móvel",{}
    return min(res,key=res.get),res

# ═══════════════════════════════════════════════════
# PLOTLY
# ═══════════════════════════════════════════════════
TH=dict(plot_bgcolor="#0D1117",paper_bgcolor="#0D1117",
        font=dict(color="#6E7681",family="Inter"),
        xaxis=dict(gridcolor="#1C2333",linecolor="#1C2333",tickfont=dict(size=9)),
        yaxis=dict(gridcolor="#1C2333",linecolor="#1C2333",tickfont=dict(size=9)),
        margin=dict(l=8,r=8,t=32,b=8),
        legend=dict(bgcolor="#161B27",bordercolor="#21262D",font=dict(size=9)))

def gl(df,campos,titulo,cx=None):
    fig=go.Figure()
    for i,c in enumerate(campos):
        if c not in df.columns: continue
        x=df[cx] if cx and cx in df.columns else df.index
        fig.add_trace(go.Scatter(x=x,y=pd.to_numeric(df[c],errors="coerce"),name=c,
          mode="lines+markers",line=dict(color=CORES[i%len(CORES)],width=2),marker=dict(size=4)))
    fig.update_layout(title=dict(text=titulo,font=dict(size=12,color="#E6EDF3")),**TH)
    return fig

def gb(df,campo,titulo,cx=None):
    v=pd.to_numeric(df[campo],errors="coerce") if campo in df.columns else pd.Series()
    x=df[cx].astype(str) if cx and cx in df.columns else pd.Series(range(len(df))).astype(str)
    cs=["#00D4AA" if val>=0 else "#F85149" for val in v]
    fig=go.Figure(go.Bar(x=x,y=v,marker_color=cs,text=[fmt(val) for val in v],
      textposition="outside",textfont=dict(size=8)))
    fig.update_layout(title=dict(text=titulo,font=dict(size=12,color="#E6EDF3")),**TH)
    return fig

def gauge(val,titulo,mn=0,mx=100,c="#2176FF"):
    fig=go.Figure(go.Indicator(mode="gauge+number",value=val,
      title={"text":titulo,"font":{"color":"#C9D1D9","size":11}},
      gauge=dict(axis=dict(range=[mn,mx],tickcolor="#484F58"),bar=dict(color=c),
        bgcolor="#161B27",bordercolor="#21262D",
        steps=[dict(range=[mn,mn+(mx-mn)*.33],color="#F8514910"),
               dict(range=[mn+(mx-mn)*.33,mn+(mx-mn)*.66],color="#FFB62710"),
               dict(range=[mn+(mx-mn)*.66,mx],color="#00D4AA10")]),
      number=dict(font=dict(color="#E6EDF3",size=24))))
    fig.update_layout(paper_bgcolor="#161B27",font=dict(color="#6E7681"),
      margin=dict(l=16,r=16,t=44,b=8),height=190)
    return fig

# ═══════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════
_cfg=load_cfg()
_defs={"pg":"home","cid":None,
       "api_key":_cfg.get("anthropic_api_key",""),
       "df_raw":None,"projecoes":{},"saldo_ini":0.,
       "entradas_vista":0.,"freq_fluxo":"Mensal","log":[]}
for k,v in _defs.items():
    if k not in st.session_state: st.session_state[k]=v

def ir(p): st.session_state.pg=p; st.rerun()
def addlog(t,tp="ok"):
    i={"ok":"✅","w":"⚠️","e":"❌","i":"ℹ️"}.get(tp,"•")
    st.session_state.log.insert(0,f"{datetime.now().strftime('%H:%M')} {i} {t}")

def get_df():
    if st.session_state.df_raw is not None:
        return calcular(st.session_state.df_raw)
    if st.session_state.cid:
        df=load_df(st.session_state.cid)
        if df is not None:
            st.session_state.df_raw=df
            return calcular(df)
    return None

# ═══════════════════════════════════════════════════
# SIDEBAR — botões simples sem HTML wrapper
# ═══════════════════════════════════════════════════
with st.sidebar:

    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_netexame.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <div style="padding:10px 0 14px;text-align:center">
          <img src="data:image/png;base64,{logo_b64}"
            style="width:100%;max-width:190px;margin-bottom:4px"/>
          <div style="color:#484F58;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;margin-top:2px">
            Analytics BI
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:10px 0 14px;text-align:center">
          <div style="font-size:1rem;font-weight:800;color:#E6EDF3">📊 NetExame</div>
          <div style="color:#484F58;font-size:.65rem;margin-top:2px">Analytics BI</div>
        </div>""", unsafe_allow_html=True)    

    # API Key — protegida por senha master
    if st.session_state.api_key:
        tp="🟠 OpenAI" if not st.session_state.api_key.startswith("sk-ant-") else "🔵 Claude"
        st.caption(f"🟢 {tp} ativa")
    with st.expander("🔑 Alterar API Key"):
        senha_ak=st.text_input("Senha master",type="password",key="senha_ak")
        if senha_ak==SENHA_MASTER:
            ak=st.text_input("Nova API Key",value="",type="password",
              placeholder="sk-ant-... ou sk-proj-...",key="nova_ak")
            if st.button("💾 Salvar",key="btn_ak",use_container_width=True):
                if ak:
                    st.session_state.api_key=ak
                    c=load_cfg(); c["anthropic_api_key"]=ak; save_cfg(c)
                    st.success("✅ Salva!")
        elif senha_ak:
            st.markdown('<div class="al-d">❌ Senha incorreta</div>',unsafe_allow_html=True)

    # Cliente ativo
    perf=load_cli(st.session_state.cid) if st.session_state.cid else None
    if perf:
        st.markdown(f"""<div style="background:#161B27;border:1px solid #21262D;border-radius:9px;
          padding:9px 12px;margin:6px 0 10px"><div style="color:#484F58;font-size:.62rem;
          text-transform:uppercase;letter-spacing:.08em">Cliente</div>
          <div style="color:#E6EDF3;font-weight:600;font-size:.86rem">{perf['nome']}</div></div>""",
          unsafe_allow_html=True)

    st.divider()

    # GESTÃO
    st.caption("GESTÃO")
    if st.button("👥 Clientes",        key="sb_clientes",   use_container_width=True): ir("clientes")
    if st.button("➕ Novo Cliente",     key="sb_novo",        use_container_width=True): ir("novo")
    if st.button("⚙️ Configurações",   key="sb_config",      use_container_width=True): ir("config")

    st.divider()
    st.caption("IMPORTAR")
    if st.button("📥 Importar Dados",  key="sb_importar",   use_container_width=True): ir("importar")
    if st.button("🔌 Integração ERP",  key="sb_erp",         use_container_width=True): ir("erp")

    st.divider()
    st.caption("DASHBOARDS")
    if st.button("🏠 Home",            key="sb_home",        use_container_width=True): ir("home")
    if st.button("📊 DRE",             key="sb_dre",         use_container_width=True): ir("dre")
    if st.button("💰 Fluxo de Caixa",  key="sb_fluxo",       use_container_width=True): ir("fluxo")
    if st.button("🏦 Balanço",         key="sb_balanco",     use_container_width=True): ir("balanco")
    if st.button("📈 Indicadores",     key="sb_indicadores", use_container_width=True): ir("indicadores")

    st.divider()
    st.caption("INTELIGÊNCIA")
    if st.button("🚨 Alertas",         key="sb_alertas",     use_container_width=True): ir("alertas")
    if st.button("🔮 Projeções ML",    key="sb_ml",          use_container_width=True): ir("ml")
    if st.button("📊 Cenários FP&A",   key="sb_cenarios",    use_container_width=True): ir("cenarios")
    if st.button("💾 Exportar",        key="sb_exportar",    use_container_width=True): ir("exportar")

# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════
def hdr(titulo,sub=""):
    st.markdown(f'<div class="phdr"><h1>{titulo}</h1><p>{sub}</p></div>',unsafe_allow_html=True)

def mc(col,lbl,val,cls="",sub=""):
    col.markdown(f'<div class="mc"><div class="mc-lbl">{lbl}</div>'
                 f'<div class="mc-val {cls}">{val}</div>'
                 f'<div class="mc-sub">{sub}</div></div>',unsafe_allow_html=True)

def sec(txt):
    st.markdown(f'<div class="sec">{txt}</div>',unsafe_allow_html=True)

def no_data():
    st.markdown('<div class="al-w">⚠️ Nenhum dado carregado. Use <b>📥 Importar Dados</b> ou <b>🔌 Integração ERP</b> no menu.</div>',unsafe_allow_html=True)

def cls_pct(v,inv=False):
    if abs(v)<0.5: return "neu"
    if inv: return "neg" if v>0 else "pos"
    return "pos" if v>0 else "neg"

# ═══════════════════════════════════════════════════
# PÁGINAS
# ═══════════════════════════════════════════════════
pg=st.session_state.pg

# ── HOME ────────────────────────────────────────────
if pg=="home":
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_netexame.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="text-align:center;margin-bottom:12px"><img src="data:image/png;base64,{logo_b64}" style="max-height:75px"/></div>',unsafe_allow_html=True)
    df=get_df()
    if df is None:
        st.markdown('<div class="al-i">👋 Bem-vindo ao <b>NetExame Analytics BI</b>! Siga os passos abaixo para começar.</div>',unsafe_allow_html=True)
        c1,c2,c3=st.columns(3)
        c1.markdown('<div class="mc"><div class="mc-lbl">Passo 1</div><div class="mc-val b">➕</div><div class="mc-sub">Cadastre um cliente em<br><b>Novo Cliente</b></div></div>',unsafe_allow_html=True)
        c2.markdown('<div class="mc"><div class="mc-lbl">Passo 2</div><div class="mc-val b">📥</div><div class="mc-sub">Importe os dados em<br><b>Importar Dados</b></div></div>',unsafe_allow_html=True)
        c3.markdown('<div class="mc"><div class="mc-lbl">Passo 3</div><div class="mc-val b">📊</div><div class="mc-sub">Acesse os dashboards no<br><b>menu lateral</b></div></div>',unsafe_allow_html=True)
        st.markdown("""<div style="margin-top:28px;background:#161B27;border:1px solid #21262D;border-radius:12px;padding:24px 28px">
          <div style="font-weight:700;color:#E6EDF3;font-size:1rem;margin-bottom:14px">O que o NetExame Analytics BI faz por você</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div style="color:#6E7681;font-size:.84rem">📊 <b style="color:#C9D1D9">DRE completa</b> com AV% e AH%</div>
            <div style="color:#6E7681;font-size:.84rem">💰 <b style="color:#C9D1D9">Fluxo de Caixa</b> com alertas automáticos</div>
            <div style="color:#6E7681;font-size:.84rem">🏦 <b style="color:#C9D1D9">Balanço Patrimonial</b> estruturado</div>
            <div style="color:#6E7681;font-size:.84rem">📈 <b style="color:#C9D1D9">15+ indicadores</b> calculados automaticamente</div>
            <div style="color:#6E7681;font-size:.84rem">🤖 <b style="color:#C9D1D9">IA</b> lê qualquer layout de arquivo</div>
            <div style="color:#6E7681;font-size:.84rem">🔮 <b style="color:#C9D1D9">Machine Learning</b> para projeções futuras</div>
            <div style="color:#6E7681;font-size:.84rem">📊 <b style="color:#C9D1D9">FP&A completo</b> — DRE, Balanço e Fluxo projetados</div>
            <div style="color:#6E7681;font-size:.84rem">🎯 <b style="color:#C9D1D9">Cenários</b> Pessimista, Base e Otimista</div>
            <div style="color:#6E7681;font-size:.84rem">🔌 <b style="color:#C9D1D9">Omie e Conta Azul</b> via API</div>
            <div style="color:#6E7681;font-size:.84rem">💾 <b style="color:#C9D1D9">Exporta</b> para Power BI, Excel, CSV, JSON</div>
          </div></div>""",unsafe_allow_html=True)
        st.stop()
    cm=cm_(df); ca=ca_(df)
    sec("🔎 Período")
    col_f1,col_f2=st.columns(2)
    anos_disp=["Todos"]+[str(a) for a in sorted(df[ca].dropna().unique().tolist())] if ca else ["Todos"]
    ano_sel=col_f1.selectbox("Ano",anos_disp,key="home_ano")
    df_fil=df[df[ca].astype(str)==ano_sel] if ano_sel!="Todos" else df.copy()
    meses_disp=["Todos"]+df_fil[cm].dropna().unique().tolist() if cm else ["Todos"]
    mes_sel=col_f2.selectbox("Mês",meses_disp,key="home_mes")
    df_fil=df_fil[df_fil[cm]==mes_sel] if mes_sel!="Todos" else df_fil
    if df_fil.empty: st.warning("Sem dados para este período."); st.stop()
    ul=df_fil.iloc[-1]
    ul_mes = str(ul.get(cm,""))
    ul_ano = str(ul.get(ca,""))
    if mes_sel=="Todos" and ano_sel=="Todos":
        periodo=f"Último período: {ul_mes}/{ul_ano} | Evolução: todos os meses"
    elif mes_sel=="Todos":
        periodo=f"Ano {ano_sel} | Último mês: {ul_mes}"
    else:
        periodo=f"{mes_sel} / {ano_sel}"
    sc=float(df_fil["score_risco"].mean()); lbl,cls_s,cor_s=score_label(sc)
    cor_num="#00D4AA" if sc>=65 else ("#FFB627" if sc>=45 else "#F85149")
    sec(f"🎯 Score de Saúde — {periodo}")
    col_score,col_graf=st.columns([1,3])
    with col_score:
        st.markdown(f"""<div style="background:white;border:2px solid {cor_num};border-radius:16px;
          padding:28px 16px;text-align:center;margin-bottom:8px;
          box-shadow:0 4px 12px rgba(0,0,0,.08)">
          <div style="font-size:3.2rem;font-weight:800;color:{cor_num};line-height:1">{sc:.0f}</div>
          <div style="color:#9CA3AF;font-size:.72rem;margin:4px 0 10px">/ 100</div>
          <div style="color:{cor_num};font-size:.88rem;font-weight:700">{lbl}</div>
        </div>""",unsafe_allow_html=True)
        with st.expander("ℹ️ Como é calculado"):
            st.markdown("""**Score de Saúde (0–100)**

4 indicadores com peso igual de **25% cada**:

🔵 **Kanitz** — normalizado entre -4 e 0
🔵 **Liquidez Imediata** — normalizado entre 0% e 5%
🔵 **EBITDA %** — normalizado entre 0% e 5%
🔵 **Ciclo de Caixa** — normalizado entre 0 e 120 dias (invertido)

**Faixas:**
- 80–100 → 🟢 Baixo Risco
- 60–79 → 🟡 Risco Moderado
- 40–59 → 🟠 Alto Risco
- 20–39 → 🔴 Risco Crítico
- 0–19 → ⚫ Insolvência Iminente""")
    with col_graf:
        if "score_risco" in df_fil.columns and len(df_fil)>1:
            x=df_fil[cm].astype(str) if cm else pd.Series(range(len(df_fil))).astype(str)
            fig_sc=go.Figure()
            fig_sc.add_trace(go.Scatter(x=x,y=df_fil["score_risco"],fill="tozeroy",mode="lines+markers",
              line=dict(color=cor_num,width=2.5),fillcolor="rgba(33,212,170,.06)",
              marker=dict(size=5,color=cor_num,line=dict(color="#0D1117",width=1.5))))
            fig_sc.add_hline(y=65,line_dash="dash",line_color="#00D4AA",opacity=0.25)
            fig_sc.add_hline(y=45,line_dash="dash",line_color="#FFB627",opacity=0.25)
            fig_sc.add_hline(y=30,line_dash="dash",line_color="#F85149",opacity=0.25)
            fig_sc.update_layout(plot_bgcolor="white",paper_bgcolor="white",
              font=dict(color="#6B7280",size=10),margin=dict(l=8,r=8,t=12,b=8),
              xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False),
              yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",range=[0,100]),
              height=200,showlegend=False)
            st.plotly_chart(fig_sc,use_container_width=True)
    sec(f"📌 KPIs — {periodo}")
    def kcard(col,lbl,campo,t="brl",inv=False):
        try:
            v=float(ul.get(campo,0) or 0); c_=cor(v,inv)
            sub=""
            if mes_sel!="Todos" and ca and cm:
                # Mesmo mês ano anterior
                ano_ant=str(int(ul.get(ca,2024))-1)
                df_ant=df[(df[ca].astype(str)==ano_ant)&(df[cm]==mes_sel)]
                if not df_ant.empty:
                    v_ant=float(df_ant.iloc[-1].get(campo,0) or 0)
                    if v_ant!=0:
                        var=safe(v-v_ant,abs(v_ant))*100
                        arr="▲" if var>0 else "▼"
                        sub=f'{arr} {abs(var):.1f}% vs {mes_sel}/{ano_ant}'
            elif len(df_fil)>1:
                # Mês anterior
                v_ant=float(df_fil.iloc[-2].get(campo,0) or 0)
                if v_ant!=0:
                    var=safe(v-v_ant,abs(v_ant))*100
                    arr="▲" if var>0 else "▼"
                    sub=f'{arr} {abs(var):.1f}% vs mês anterior'
            col.markdown(f'<div class="mc"><div class="mc-lbl">{lbl}</div><div class="mc-val {c_}">{fmt(v,t)}</div><div class="mc-sub">{sub}</div></div>',unsafe_allow_html=True)
        except: col.markdown(f'<div class="mc"><div class="mc-lbl">{lbl}</div><div class="mc-val">—</div></div>',unsafe_allow_html=True)
    r1=st.columns(4)
    kcard(r1[0],"💰 Receita Bruta","receita bruta de vendas")
    kcard(r1[1],"📊 Receita Líquida","receita líquida")
    kcard(r1[2],"📈 Lucro Bruto","lucro bruto")
    kcard(r1[3],"✅ Lucro Líquido","lucro líquido")
    r2=st.columns(4)
    kcard(r2[0],"⚡ EBITDA %","EBITDA %","pct")
    kcard(r2[1],"📉 Margem Líquida","margem líquida %","pct")
    kcard(r2[2],"🌡️ Kanitz","kanitz","pct")
    kcard(r2[3],"💧 Liquidez Corrente","liquidez corrente","x")
    r3=st.columns(4)
    kcard(r3[0],"📅 PMR (dias)","PMR","d",True)
    kcard(r3[1],"📅 PMP (dias)","PMP","d")
    kcard(r3[2],"🔄 Ciclo de Caixa","ciclo de caixa","d",True)
    kcard(r3[3],"💹 ROE","ROE","pct")
    if len(df_fil)>1:
        sec("📈 Evolução")
        x=df_fil[cm].astype(str) if cm else pd.Series(range(len(df_fil))).astype(str)
        # Adiciona ano no eixo x para ficar claro
        if ca and cm:
            x=df_fil[cm].astype(str)+"/"+df_fil[ca].astype(str).str[-2:]
        g1,g2=st.columns(2)
        def layout_graf(titulo,ytitle):
            return dict(
                title=dict(text=titulo,font=dict(size=13,color="#111827",family="Inter"),x=0),
                plot_bgcolor="white",paper_bgcolor="white",
                font=dict(color="#6B7280",size=10,family="Inter"),
                margin=dict(l=12,r=12,t=44,b=40),
                xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",tickfont=dict(size=9),
                           tickangle=-35,showgrid=False),
                yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",
                           tickfont=dict(size=9),
                           title=dict(text=ytitle,font=dict(size=9,color="#9CA3AF")),showgrid=True),
                legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",
                            y=-0.35,font=dict(size=9),itemsizing="constant"),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",
                                font=dict(color="#111827",size=11)),
                shapes=[dict(type="rect",xref="paper",yref="paper",
                            x0=0,y0=0,x1=1,y1=1,
                            line=dict(color="#E8ECF0",width=1))])
        with g1:
            fig=go.Figure()
            for c,cor_c,nm in [
              ("receita bruta de vendas","#2176FF","Receita Bruta"),
              ("receita líquida","#00D4AA","Receita Líquida"),
              ("lucro bruto","#FFB627","Lucro Bruto"),
              ("lucro líquido","#F85149","Lucro Líquido")]:
                if c not in df_fil.columns: continue
                y=pd.to_numeric(df_fil[c],errors="coerce")
                fig.add_trace(go.Scatter(x=x,y=y,name=nm,mode="lines+markers",
                  line=dict(color=cor_c,width=2.5),
                  marker=dict(size=6,color=cor_c,line=dict(color="#161B27",width=1.5)),
                  hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>R$ %{{y:,.0f}}<extra></extra>"))
            fig.update_layout(**layout_graf("💰 Resultado Financeiro (R$)","R$"))
            st.plotly_chart(fig,use_container_width=True)
        with g2:
            fig2=go.Figure()
            for c,cor_c,nm in [
              ("margem bruta %","#2176FF","Margem Bruta"),
              ("margem contrib %","#00D4AA","Margem Contribuição"),
              ("margem líquida %","#FFB627","Margem Líquida"),
              ("EBITDA %","#F85149","EBITDA")]:
                if c not in df_fil.columns: continue
                y=pd.to_numeric(df_fil[c],errors="coerce")
                fig2.add_trace(go.Scatter(x=x,y=y,name=nm,mode="lines+markers",
                  line=dict(color=cor_c,width=2.5),
                  marker=dict(size=6,color=cor_c,line=dict(color="#161B27",width=1.5)),
                  hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>%{{y:.1f}}%<extra></extra>"))
            fig2.update_layout(**layout_graf("📊 Margens (%)","% sobre Receita Líquida"))
            st.plotly_chart(fig2,use_container_width=True)
    if mes_sel=="Todos" and len(df_fil)>=6:
        sec("🔮 Projeção — Próximo Mês")
        mds=[m for m,ok in MODELOS_ML.items() if ok]
        cols_proj=st.columns(3)
        projs_home={}
        for cp2,campo_p,lbl_p in zip(cols_proj,["receita bruta de vendas","lucro líquido","EBITDA"],["Receita Bruta","Lucro Líquido","EBITDA"]):
            if campo_p not in df_fil.columns: continue
            try:
                melhor,_=melhor_modelo(df_fil[campo_p],mds[:3])
                proj=treinar(df_fil[campo_p],melhor,1)
                if proj is not None:
                    v_at=float(df_fil[campo_p].iloc[-1]); v_pr=float(proj.iloc[0])
                    var=safe(v_pr-v_at,abs(v_at))*100
                    mds_testados=", ".join([m for m,ok in MODELOS_ML.items() if ok])
                    cp2.markdown(f'<div class="mc"><div class="mc-lbl">📮 {lbl_p}</div>'
                                f'<div class="mc-val {cor(var)}">{fmt(v_pr)}</div>'
                                f'<div class="mc-sub">{var:+.1f}% vs último mês<br>'
                                f'<span style="font-size:.65rem;color:#9CA3AF">'
                                f'Escolhido por menor MSE: <b>{melhor}</b><br>'
                                f'Modelos testados: {mds_testados}</span></div></div>',unsafe_allow_html=True)
                    projs_home[campo_p]={"lbl":lbl_p,"modelo":melhor,"proj1":v_pr}
            except: pass

        # Expander com projeção 12 meses
        with st.expander("📈 Ver projeção dos próximos 12 meses"):
            if projs_home:
                campo_graf=st.selectbox("Campo",list(projs_home.keys()),
                  format_func=lambda x: projs_home[x]["lbl"],key="home_proj_campo")
                if campo_graf:
                    try:
                        melhor_g=projs_home[campo_graf]["modelo"]
                        proj_12=treinar(df_fil[campo_graf],melhor_g,12)
                        if proj_12 is not None:
                            x_h=df_fil[cm].astype(str) if cm else pd.Series(range(len(df_fil))).astype(str)
                            if ca and cm:
                                x_h=df_fil[cm].astype(str)+"/"+df_fil[ca].astype(str).str[-2:]
                            x_p=[f"M+{i+1}" for i in range(12)]
                            v_hist=pd.to_numeric(df_fil[campo_graf],errors="coerce")
                            fig_p12=go.Figure()
                            fig_p12.add_trace(go.Scatter(x=x_h,y=v_hist,name="Histórico",
                              mode="lines+markers",line=dict(color="#2563EB",width=2.2),
                              marker=dict(size=4,color="#2563EB",line=dict(color="white",width=1.5)),
                              hovertemplate="<b>Histórico</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>"))
                            fig_p12.add_trace(go.Scatter(x=x_p,y=proj_12.values,name=f"Projeção ({melhor_g})",
                              mode="lines+markers",line=dict(color="#059669",width=2.2,dash="dash"),
                              marker=dict(size=6,color="#059669",symbol="diamond",line=dict(color="white",width=1.5)),
                              hovertemplate="<b>Projeção</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>"))
                            # Banda ±15%
                            y_up=[v*1.15 for v in proj_12.values]
                            y_dn=[v*0.85 for v in proj_12.values]
                            fig_p12.add_trace(go.Scatter(
                              x=list(x_p)+list(x_p)[::-1],
                              y=y_up+y_dn[::-1],
                              fill="toself",fillcolor="rgba(5,150,105,.07)",
                              line=dict(color="rgba(0,0,0,0)"),name="Intervalo ±15%"))
                            fig_p12.update_layout(
                              title=dict(text=f"Projeção 12 meses — {projs_home[campo_graf]['lbl']} ({melhor_g})",
                                font=dict(size=12,color="#111827")),
                              plot_bgcolor="white",paper_bgcolor="white",
                              font=dict(color="#6B7280",size=10),
                              margin=dict(l=8,r=8,t=44,b=40),
                              xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
                              yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
                              legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
                              hovermode="x unified",
                              hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))
                            st.plotly_chart(fig_p12,use_container_width=True)
                            # Tabela resumo
                            resumo_12=pd.DataFrame({
                                "Período":x_p,
                                "Projeção":[fmt(v) for v in proj_12.values],
                                "Pessimista (-15%)":[fmt(v*0.85) for v in proj_12.values],
                                "Otimista (+15%)":[fmt(v*1.15) for v in proj_12.values]})
                            st.dataframe(resumo_12,use_container_width=True,hide_index=True)
                    except: st.warning("Não foi possível gerar a projeção de 12 meses.")

# ── CLIENTES ────────────────────────────────────────
elif pg=="clientes":
    hdr("👥 Clientes")
    cls=ls_cli()
    if not cls:
        st.markdown('<div class="al-i">Nenhum cliente ainda. Clique em <b>➕ Novo Cliente</b>.</div>',unsafe_allow_html=True)

    # PIN pendente
    if "pin_pendente" not in st.session_state: st.session_state.pin_pendente=None

    for c in cls:
        c1,c2,c3,c4=st.columns([4,2,1,1])
        p2=load_cli(c["id"]); tem_pin=bool(p2.get("pin","")) if p2 else False
        c1.markdown(f'<div style="color:#111827;font-weight:600;padding:10px 0">'
                   f'{c["nome"]} {"🔒" if tem_pin else "🔓"}</div>',unsafe_allow_html=True)
        c2.markdown(f'<div style="color:#9CA3AF;font-size:.82rem;padding:12px 0">🕐 {c["at"]}</div>',unsafe_allow_html=True)
        if c3.button("📂 Abrir",key=f"ab_{c['id']}",use_container_width=True):
            if tem_pin:
                st.session_state.pin_pendente=c["id"]
            else:
                p_open=load_cli(c["id"])
                st.session_state.cid=c["id"]
                st.session_state.df_raw=load_df(c["id"])
                st.session_state.projecoes={}
                st.session_state.saldo_ini=float(p_open.get("saldo_ini",0)) if p_open else 0.
                st.session_state.entradas_vista=float(p_open.get("entradas_vista",0)) if p_open else 0.
                st.session_state.freq_fluxo=p_open.get("freq_fluxo","Mensal") if p_open else "Mensal"
                addlog(f"'{c['nome']}' aberto"); ir("home")
        if c4.button("🗑",key=f"dl_{c['id']}",use_container_width=True):
            os.remove(path_cli(c["id"]))
            if st.session_state.cid==c["id"]: st.session_state.cid=None; st.session_state.df_raw=None
            st.rerun()
        st.divider()

    # Caixa de PIN
    if st.session_state.pin_pendente:
        cid_p=st.session_state.pin_pendente
        p3=load_cli(cid_p)
        st.markdown(f'<div class="al-i">🔒 Digite o PIN para acessar <b>{p3["nome"] if p3 else "?"}</b></div>',unsafe_allow_html=True)
        pin_dig=st.text_input("PIN",type="password",key="pin_input",max_chars=10)
        col_ok,col_cancel=st.columns(2)
        if col_ok.button("✅ Confirmar",use_container_width=True):
            if verificar_pin(cid_p,pin_dig):
                p_pin=load_cli(cid_p)
                st.session_state.cid=cid_p
                st.session_state.df_raw=load_df(cid_p)
                st.session_state.projecoes={}
                st.session_state.saldo_ini=float(p_pin.get("saldo_ini",0)) if p_pin else 0.
                st.session_state.entradas_vista=float(p_pin.get("entradas_vista",0)) if p_pin else 0.
                st.session_state.freq_fluxo=p_pin.get("freq_fluxo","Mensal") if p_pin else "Mensal"
                st.session_state.pin_pendente=None
                addlog(f"Acesso autorizado"); ir("home")
            else:
                st.markdown('<div class="al-d">❌ PIN incorreto.</div>',unsafe_allow_html=True)
        if col_cancel.button("❌ Cancelar",use_container_width=True):
            st.session_state.pin_pendente=None; st.rerun()

    # Gerenciar PINs (senha master)
    st.divider()
    with st.expander("🔐 Gerenciar PINs — Acesso Restrito"):
        senha=st.text_input("Senha master",type="password",key="senha_master")
        if senha==SENHA_MASTER:
            st.markdown('<div class="al-s">✅ Acesso autorizado</div>',unsafe_allow_html=True)
            cli_sel=st.selectbox("Cliente",["Selecione"]+[c["nome"] for c in cls])
            if cli_sel!="Selecione":
                cid_sel=next(c["id"] for c in cls if c["nome"]==cli_sel)
                p4=load_cli(cid_sel)
                pin_atual=p4.get("pin","") if p4 else ""
                st.markdown(f'PIN atual: **{"configurado" if pin_atual else "sem PIN"}**')
                novo_pin=st.text_input("Novo PIN (deixe vazio para remover)",
                                       type="password",key="novo_pin",max_chars=10)
                if st.button("💾 Salvar PIN",use_container_width=True):
                    if p4:
                        p4["pin"]=novo_pin
                        salvar_cli(cid_sel,p4)
                        if novo_pin:
                            st.markdown(f'<div class="al-s">✅ PIN configurado para {cli_sel}</div>',unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="al-s">✅ PIN removido de {cli_sel}</div>',unsafe_allow_html=True)
        elif senha:
            st.markdown('<div class="al-d">❌ Senha incorreta</div>',unsafe_allow_html=True)

# ── NOVO CLIENTE ────────────────────────────────────
elif pg=="novo":
    hdr("➕ Novo Cliente")
    nome=st.text_input("Nome da empresa *",placeholder="Ex: Empresa ABC Ltda")
    if st.button("✅ Cadastrar",use_container_width=True):
        if not nome.strip(): st.error("Informe o nome.")
        else:
            cid=gid(nome); salvar_cli(cid,{"nome":nome.strip()})
            st.session_state.cid=cid
            st.session_state.df_raw=None
            st.session_state.projecoes={}
            st.session_state.saldo_ini=0.
            st.session_state.entradas_vista=0.
            st.session_state.freq_fluxo="Mensal"
            addlog(f"'{nome}' cadastrado"); st.success(f"✅ {nome} cadastrado!"); time.sleep(1); ir("config")

# ── CONFIGURAÇÕES ───────────────────────────────────
elif pg=="config":
    hdr("⚙️ Configurações","API Key, saldo inicial e preferências")
    p2=load_cli(st.session_state.cid) if st.session_state.cid else None
    if p2:
        st.markdown(f'<div class="al-i">👤 Cliente ativo: <b>{p2["nome"]}</b></div>',unsafe_allow_html=True)
    sec("🔑 API Key — OpenAI ou Claude")
    st.markdown('<div class="al-i">Cole aqui sua chave da OpenAI (sk-proj-...) ou Claude (sk-ant-...). A IA usa essa chave para ler os arquivos e extrair dados automaticamente.</div>',unsafe_allow_html=True)
    if st.session_state.api_key:
        tp2="🟠 OpenAI" if not st.session_state.api_key.startswith("sk-ant-") else "🔵 Claude"
        st.markdown(f'<div class="al-s">🟢 {tp2} ativa</div>',unsafe_allow_html=True)
    senha_cfg=st.text_input("Senha master para alterar",type="password",key="senha_cfg")
    if senha_cfg==SENHA_MASTER:
        ak2=st.text_input("Nova API Key",value="",type="password",
          placeholder="sk-proj-... ou sk-ant-...",key="ak2_cfg")
    elif senha_cfg:
        st.markdown('<div class="al-d">❌ Senha incorreta</div>',unsafe_allow_html=True)
        ak2=""
    else:
        ak2=""
    sec("💰 Saldo Inicial de Caixa")
    si=st.number_input("Saldo inicial (R$)",value=float(st.session_state.saldo_ini),step=1000.,format="%.2f")
    sec("💵 Entradas à Vista")
    st.markdown('<div class="al-i">Valor fixo de entradas à vista somado automaticamente ao Fluxo de Caixa.</div>',unsafe_allow_html=True)
    ev_atual=float(p2.get("entradas_vista",0)) if p2 else 0.
    ev=st.number_input("Valor das Entradas à Vista (R$)",value=ev_atual,step=100.,format="%.2f")
    freq_atual=p2.get("freq_fluxo","Mensal") if p2 else "Mensal"
    freq_sel=st.radio("Frequência",["Mensal","Diário"],
      index=0 if freq_atual=="Mensal" else 1,horizontal=True,
      help="Mensal: soma R$ X por mês | Diário: soma R$ X × 22 dias úteis")
    if st.button("💾 Salvar Configurações",use_container_width=True):
        st.session_state.saldo_ini=si
        st.session_state.entradas_vista=ev
        st.session_state.freq_fluxo=freq_sel
        if ak2 and senha_cfg==SENHA_MASTER:
            st.session_state.api_key=ak2
            c=load_cfg(); c["anthropic_api_key"]=ak2; save_cfg(c)
        if p2:
            p2["saldo_ini"]=si
            p2["entradas_vista"]=ev
            p2["freq_fluxo"]=freq_sel
            salvar_cli(st.session_state.cid,p2)
        st.success("✅ Configurações salvas!"); time.sleep(1); ir("importar")

# ── IMPORTAR ────────────────────────────────────────
elif pg=="importar":
    hdr("📥 Importar Dados","A IA lê qualquer layout — DRE horizontal, vertical, PDF, CSV, Excel")
    if not st.session_state.cid:
        st.markdown('<div class="al-w">⚠️ Cadastre e selecione um cliente primeiro.</div>',unsafe_allow_html=True); st.stop()
    if not st.session_state.api_key:
        st.markdown('<div class="al-w">⚠️ Configure a API Key em <b>⚙️ Configurações</b> primeiro.</div>',unsafe_allow_html=True)
    p2=load_cli(st.session_state.cid)
    st.markdown(f'<div class="al-i">👤 <b>{p2["nome"] if p2 else "?"}</b> — Importe um arquivo por vez (DRE, Balanço, Fluxo) para máxima precisão.</div>',unsafe_allow_html=True)
    arqs=st.file_uploader("Selecione o(s) arquivo(s)",type=["pdf","xlsx","xls","xlsm","csv"],accept_multiple_files=True)
    col_ia, col_dir = st.columns(2)
    btn_ia  = col_ia.button("🤖 Processar com IA",use_container_width=True)
    btn_dir = col_dir.button("⚡ Leitura Direta (CSV/Excel padrão)",use_container_width=True)
    if arqs and btn_dir:
        dfs_dir=[]
        for a in arqs:
            b=a.read(); n=a.name.lower()
            try:
                if n.endswith(".csv"):
                    for enc in ["utf-8-sig","utf-8","latin1","cp1252"]:
                        for sep in [";",","]:
                            try:
                                df_tmp=pd.read_csv(io.BytesIO(b),sep=sep,decimal=",",encoding=enc,on_bad_lines="skip")
                                # Corrige mojibake (UTF-8 lido como Latin-1/CP1252) nos nomes das colunas
                                if enc in ("latin1","cp1252"):
                                    novas_cols=[]
                                    for c in df_tmp.columns:
                                        try:
                                            c_fix=str(c).encode("latin1").decode("utf-8")
                                            novas_cols.append(c_fix)
                                        except: novas_cols.append(c)
                                    df_tmp.columns=novas_cols
                                if df_tmp.shape[1]>=5 and any(c.lower() in ["mês","mes"] for c in df_tmp.columns):
                                    dfs_dir.append(df_tmp); break
                            except: pass
                        else: continue
                        break
                else:
                    xls=pd.read_excel(io.BytesIO(b),sheet_name=None)
                    for s,df_tmp in xls.items():
                        if any(c.lower() in ["mês","mes"] for c in df_tmp.columns):
                            dfs_dir.append(df_tmp); break
            except Exception as e: st.markdown(f'<div class="al-d">❌ {a.name}: {e}</div>',unsafe_allow_html=True)
        if dfs_dir:
            df_final=pd.concat(dfs_dir,ignore_index=True)
            # Padroniza colunas
            rename_map={}
            for c in df_final.columns:
                cl=c.lower().strip()
                if cl=="receita líquida de vendas": rename_map[c]="receita líquida"
                if cl in ["mês","mes"]: rename_map[c]="mês"
                if cl in ["ano","year"]: rename_map[c]="Ano"
            df_final=df_final.rename(columns=rename_map)
            # Ordena por data
            try:
                mes_num={"jan":"01","fev":"02","mar":"03","abr":"04","mai":"05","jun":"06",
                         "jul":"07","ago":"08","set":"09","out":"10","nov":"11","dez":"12"}
                df_final["_data"]=pd.to_datetime(
                    df_final["Ano"].astype(str)+"-"+
                    df_final["mês"].astype(str).str.lower().str[:3].map(mes_num).fillna("01")+"-01",
                    errors="coerce")
                df_final=df_final.sort_values("_data").drop(columns=["_data"]).reset_index(drop=True)
            except: pass
            # Identifica colunas extras que não fazem parte do padrão do sistema (TODOS + Ano/mês/Data)
            # e soma automaticamente em Disponibilidades entradas/Saida, sem perder o dinheiro de vista
            campos_calculados_sistema={
                "deduções","receita líquida","lucro bruto","margem contrib","desp op",
                "lucro operacional","resultado IR","lucro líquido","EBITDA",
                "margem bruta %","margem contrib %","margem op %","margem líquida %","EBITDA %",
                "ativo circ","ativo total","pass circ","pass total","PL",
                "liquidez corrente","liquidez imediata","ROE","kanitz","PMR","PMP","PME",
                "ciclo de caixa","giro estoque","ticket médio","ICD",
                "saldo período","saldo acumulado","score_risco",
                # Variações de nome vindas do arquivo do cliente (sinônimos comuns)
                "deduções da receita bruta","receita líquida de vendas","despesas operacionais totais",
                "resultado antes da provisão para imposto de renda e contribuição social",
                "ativo total saldo","passivo total saldo","ativo circulante saldo","passivo circulante saldo",
                "patrimônio líquido","Lucratividade","Margem de Contribuição",
                "Prazo médio de pagamentos","Prazo médio de recebimentos","Prazo médio de estocagem",
                "giro do estoque","termômetro de kanitz","roe","ticket medio",
            }
            campos_padrao_conhecidos=set(TODOS)|campos_calculados_sistema|{"Ano","mês","Data","Item"}
            # Palavras que indicam que a coluna é um INDICADOR/MÉTRICA, não dinheiro real —
            # essas colunas NÃO devem ser somadas ao Fluxo de Caixa
            pistas_indicador=["inadimp","obsol","índice","indice","%","percentual","taxa de",
                              "ratio","score","nota","grau"]
            campos_extras=[c for c in df_final.columns if c not in campos_padrao_conhecidos
                          and pd.api.types.is_numeric_dtype(df_final[c])
                          and not any(p in c.lower() for p in pistas_indicador)]
            campos_ignorados=[c for c in df_final.columns if c not in campos_padrao_conhecidos
                             and pd.api.types.is_numeric_dtype(df_final[c])
                             and any(p in c.lower() for p in pistas_indicador)]

            pistas_entrada_dir=["receita","entrada","recebiment","venda","faturamento","comiss","repasse"]
            pistas_saida_dir=["despesa","saida","saída","pagamento","custo","gasto","manutenç","marketing","honorári","taxa"]

            detalhamento_dir=[]
            if campos_extras and "mês" in df_final.columns and "Ano" in df_final.columns:
                if "Disponibilidades entradas" not in df_final.columns:
                    df_final["Disponibilidades entradas"]=0.
                if "Disponibilidades Saida" not in df_final.columns:
                    df_final["Disponibilidades Saida"]=0.
                for campo_extra in campos_extras:
                    col_l=campo_extra.lower()
                    eh_saida=any(p in col_l for p in pistas_saida_dir)
                    campo_destino="Disponibilidades Saida" if eh_saida else "Disponibilidades entradas"
                    for idx,row in df_final.iterrows():
                        v=float(row.get(campo_extra,0) or 0)
                        if v==0: continue
                        df_final.at[idx,campo_destino]=float(df_final.at[idx,campo_destino] or 0)+v
                        detalhamento_dir.append({"ano":str(row.get("Ano","")),
                                                 "mes":str(row.get("mês","")).lower()[:3],
                                                 "campo_pai":campo_destino,
                                                 "subconta":campo_extra,"valor":v})

            if detalhamento_dir and st.session_state.cid:
                df_detalhe_dir=pd.DataFrame(detalhamento_dir)
                path_detalhe_dir=os.path.join(PASTA,f"{gid(st.session_state.cid)}_detalhamento.csv")
                if os.path.exists(path_detalhe_dir):
                    df_detalhe_antigo_dir=pd.read_csv(path_detalhe_dir,sep=";",decimal=",",encoding="utf-8-sig")
                    df_detalhe_antigo_dir["ano"]=df_detalhe_antigo_dir["ano"].astype(str)
                    df_detalhe_dir["ano"]=df_detalhe_dir["ano"].astype(str)
                    df_detalhe_dir=pd.concat([df_detalhe_antigo_dir,df_detalhe_dir],ignore_index=True).drop_duplicates(
                        subset=["ano","mes","campo_pai","subconta"],keep="last")
                df_detalhe_dir.to_csv(path_detalhe_dir,sep=";",decimal=",",index=False,encoding="utf-8-sig")

            st.session_state.df_raw=df_final
            save_df(st.session_state.cid,df_final)
            st.markdown(f'<div class="al-s">✅ Leitura direta: <b>{len(df_final)}</b> períodos × <b>{df_final.shape[1]}</b> campos</div>',unsafe_allow_html=True)
            if campos_extras:
                with st.expander(f"⚠️ {len(campos_extras)} coluna(s) extra(s) somadas em Entradas/Saídas (revisão recomendada)"):
                    st.markdown('<div class="al-w">Estas colunas não fazem parte do padrão do sistema, mas o valor foi preservado e somado ao total de Entradas ou Saídas do Fluxo de Caixa. Veja o detalhamento no drill-down da tela de Fluxo de Caixa.</div>',unsafe_allow_html=True)
                    st.write(campos_extras)
            if campos_ignorados:
                with st.expander(f"ℹ️ {len(campos_ignorados)} coluna(s) identificadas como indicador/métrica — não somadas ao Fluxo de Caixa"):
                    st.markdown('<div class="al-i">Estas colunas parecem ser indicadores (ex: % de inadimplência, obsolescência) e não valores monetários — por isso não foram somadas ao total de Entradas/Saídas. Os valores continuam disponíveis no banco de dados, caso queira usá-los em análises futuras.</div>',unsafe_allow_html=True)
                    st.write(campos_ignorados)
            addlog(f"Leitura direta: {len(df_final)} períodos")
        else:
            st.error("Não foi possível ler o arquivo. Tente o botão 🤖 Processar com IA.")
    if arqs and btn_ia:
        if not st.session_state.api_key:
            st.error("Configure a API Key em ⚙️ Configurações.")
        else:
            for a in arqs:
                with st.spinner(f"Lendo {a.name}..."):
                    df_r,msg=ler(a.read(),a.name)
                if df_r is None:
                    st.markdown(f'<div class="al-d">❌ {a.name}: {msg}</div>',unsafe_allow_html=True); continue
                st.markdown(f'<div class="al-s">✅ {a.name}: {msg}</div>',unsafe_allow_html=True)
                tipo_det=detectar_tipo(df_r)

                # Se o arquivo está no formato longo (vertical), usa o parser determinístico dedicado
                if eh_formato_longo(df_r) and tipo_det!="DESCONHECIDO":
                    cels=parser_formato_longo(df_r,tipo_det)
                    st.markdown(f'<div class="al-i">ℹ️ Formato vertical detectado — processado com parser determinístico (sem IA).</div>',unsafe_allow_html=True)
                else:
                    with st.spinner(f"🤖 IA extraindo dados..."):
                        cels=ia_extrair(df_r,TODOS,st.session_state.api_key)

                # Verifica se campos CRÍTICOS vieram zerados/ausentes
                campos_criticos={"DRE":["receita bruta de vendas","CMV (custo da mercadoria vendida)","lucro líquido"],
                                "BALANCO":["ativo total saldo","passivo total saldo"],
                                "FLUXO":["Disponibilidades entradas","Disponibilidades Saida"]}.get(tipo_det,[])
                campos_presentes={c.get("campo") for c in cels if "_detalhamento" not in c}
                faltando_critico=any(cc not in campos_presentes for cc in campos_criticos)

                # Verifica se a quantidade de PERÍODOS distintos é suspeita (poucos meses cobertos)
                periodos_cobertos={(c.get("ano"),c.get("mes")) for c in cels if "_detalhamento" not in c}
                poucos_periodos=len(periodos_cobertos)<6

                # Se faltou campo crítico OU poucos períodos, tenta extração bruta + regras determinísticas
                if (len(cels)<10 or faltando_critico or poucos_periodos) and st.session_state.api_key:
                    with st.spinner("🤖 Tentando extração bruta + regras determinísticas..."):
                        celulas_brutas=_chamar_ia_extracao_bruta(df_r,st.session_state.api_key,tipo_det)
                        st.caption(f"🔧 Debug: IA retornou {len(celulas_brutas)} linhas brutas")
                        cels_via_regras=mapear_celulas_brutas(celulas_brutas,tipo_det) if celulas_brutas else []
                        st.caption(f"🔧 Debug: após mapeamento por regras = {len(cels_via_regras)} campos")
                        if len(cels_via_regras)>len(cels):
                            cels=cels_via_regras
                            st.markdown(f'<div class="al-i">ℹ️ Layout não padrão — usada extração bruta por IA + soma por regras determinísticas ({len(celulas_brutas)} linhas → {len(cels_via_regras)} campos).</div>',unsafe_allow_html=True)

                if not cels:
                    st.markdown(f'<div class="al-w">⚠️ {a.name}: nenhum dado extraído.</div>',unsafe_allow_html=True)
                    continue
                # Separa o detalhamento (drill-down) e as colunas não reconhecidas das células normais
                detalhamento_arq=[]
                nao_reconhecidas_arq=[]
                cels_limpas=[]
                for c in cels:
                    if "_detalhamento" in c:
                        detalhamento_arq.extend(c["_detalhamento"])
                    elif "_nao_reconhecidas" in c:
                        nao_reconhecidas_arq.extend(c["_nao_reconhecidas"])
                    else:
                        cels_limpas.append(c)
                cels=cels_limpas

                if nao_reconhecidas_arq:
                    colunas_unicas=sorted(set(item["coluna"] for item in nao_reconhecidas_arq))
                    total_valor_nr=sum(item["valor"] for item in nao_reconhecidas_arq)
                    with st.expander(f"⚠️ {len(colunas_unicas)} coluna(s) não reconhecida(s) automaticamente — classificadas como 'Outras' (revisão recomendada)"):
                        st.markdown(f'<div class="al-w">O dinheiro foi mantido no total (R$ {total_valor_nr:,.2f} somados em "Outras"), mas o sistema não conseguiu identificar uma categoria específica para estas colunas. Para classificar corretamente, renomeie a coluna no arquivo original usando um termo mais comum (ex: "Receita de Serviços", "Fornecedores") e reimporte.</div>',unsafe_allow_html=True)
                        df_nr=pd.DataFrame(nao_reconhecidas_arq)
                        df_nr_resumo=df_nr.groupby(["coluna","destino"])["valor"].agg(["sum","count"]).reset_index()
                        df_nr_resumo.columns=["Coluna do Arquivo","Classificada como","Total (R$)","Nº de períodos"]
                        df_nr_resumo["Total (R$)"]=df_nr_resumo["Total (R$)"].apply(lambda v: fmt(v))
                        st.dataframe(df_nr_resumo,use_container_width=True,hide_index=True)
                if detalhamento_arq and st.session_state.cid:
                    df_detalhe=pd.DataFrame(detalhamento_arq)
                    path_detalhe=os.path.join(PASTA,f"{gid(st.session_state.cid)}_detalhamento.csv")
                    if os.path.exists(path_detalhe):
                        df_detalhe_antigo=pd.read_csv(path_detalhe,sep=";",decimal=",",encoding="utf-8-sig")
                        df_detalhe_antigo["ano"]=df_detalhe_antigo["ano"].astype(str)
                        df_detalhe["ano"]=df_detalhe["ano"].astype(str)
                        df_concat=pd.concat([df_detalhe_antigo,df_detalhe],ignore_index=True)
                        df_detalhe=df_concat.drop_duplicates(subset=["ano","mes","campo_pai","subconta"],keep="last")
                    df_detalhe.to_csv(path_detalhe,sep=";",decimal=",",index=False,encoding="utf-8-sig")
                demo_detectada=identificar_demonstracao(cels)
                if not demo_detectada:
                    st.markdown(f'<div class="al-w">⚠️ {a.name}: não foi possível identificar a demonstração.</div>',unsafe_allow_html=True)
                    continue
                
                df_atual=st.session_state.df_raw
                df_merged=merge_banco_por_demonstracao(df_atual,cels,demo_detectada)
                st.session_state.df_raw=df_merged
                save_df(st.session_state.cid,df_merged)
                st.markdown(f'<div class="al-s">✅ <b>{a.name}</b> identificado como <b>{demo_detectada}</b> — '
                           f'{len(cels)} células processadas, banco atualizado com <b>{len(df_merged)}</b> períodos totais.</div>',
                           unsafe_allow_html=True)
                addlog(f"{a.name}: {demo_detectada} — {len(cels)} células")

                # AUDITORIA NÃO-BLOQUEANTE: IA roda em paralelo só pra avisar discrepâncias
                if st.session_state.api_key and tipo_det in ("DRE","BALANCO","FLUXO"):
                    with st.spinner("🔍 Auditoria automática com IA (não bloqueia)..."):
                        try:
                            cels_ia_aud=_chamar_ia_extracao(df_r,TODOS,st.session_state.api_key,tipo_det)
                            st.caption(f"🔧 Debug temporário: IA retornou {len(cels_ia_aud)} células")
                            idx_parser={(c.get("ano"),c.get("mes"),c.get("campo")):c.get("valor") for c in cels}
                            idx_ia_aud={(c.get("ano"),c.get("mes"),c.get("campo")):c.get("valor") for c in cels_ia_aud}
                            alertas_aud=[]
                            campos_comparados=0
                            for chave,v_p in idx_parser.items():
                                v_i=idx_ia_aud.get(chave)
                                if v_i is not None:
                                    campos_comparados+=1
                                    try:
                                        diff=abs(float(v_p)-float(v_i))/max(abs(float(v_p)),1)*100
                                        if diff>10:
                                            alertas_aud.append((chave,v_p,v_i,diff))
                                    except: pass
                            if alertas_aud:
                                with st.expander(f"🔍 Auditoria IA — {len(alertas_aud)} possível(is) divergência(s) encontrada(s) (revisão opcional)"):
                                    st.markdown('<div class="al-i">Estes valores foram conferidos por IA e mostraram diferença relevante em relação ao parser. O banco já foi salvo com os valores do parser — revise se necessário.</div>',unsafe_allow_html=True)
                                    for (ano,mes,campo),v_p,v_i,diff in sorted(alertas_aud,key=lambda x:-x[3])[:15]:
                                        st.markdown(f'<div class="al-w">⚠️ <b>{campo}</b> — {mes}/{ano}: Parser={fmt(v_p)} vs IA={fmt(v_i)} ({diff:.0f}% diferença)</div>',unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="al-s">🔍 Auditoria IA concluída: {campos_comparados} valores comparados, '
                                           f'nenhuma divergência relevante (>10%) encontrada. Os dados do parser foram confirmados pela IA.</div>',unsafe_allow_html=True)
                        except Exception as e:
                            st.markdown(f'<div class="al-w">⚠️ Auditoria IA não pôde ser concluída ({e}). O banco já foi salvo com os valores do parser local, que são confiáveis independentemente da auditoria.</div>',unsafe_allow_html=True)
    if st.session_state.df_raw is not None and not st.session_state.df_raw.empty:
        st.divider()
        df_ex=st.session_state.df_raw; cm2=cm_(df_ex); ca2=ca_(df_ex)
        st.markdown(f'<div class="al-s">📊 Banco de dados: <b>{len(df_ex)}</b> períodos × <b>{df_ex.shape[1]}</b> campos</div>',unsafe_allow_html=True)
        if ca2: st.markdown(f'<div class="al-i">Anos: {", ".join(sorted(str(a) for a in df_ex[ca2].dropna().unique()))}</div>',unsafe_allow_html=True)

        sec("📋 Tela de Revisão — Cobertura por Demonstração")
        cobertura=gerar_cobertura(df_ex,DEMONSTRACOES_CAMPOS)
        if not cobertura.empty:
            cols_show=["Ano","Mês"]+[d for d in DEMONSTRACOES_CAMPOS.keys() if d in cobertura.columns]
            cols_qtd=[f"{d}_qtd" for d in DEMONSTRACOES_CAMPOS.keys() if f"{d}_qtd" in cobertura.columns]
            st.dataframe(cobertura[cols_show],use_container_width=True,hide_index=True,height=min(400,40+len(cobertura)*36))
            with st.expander("📊 Ver detalhamento de campos preenchidos por período"):
                st.dataframe(cobertura[["Ano","Mês"]+cols_qtd],use_container_width=True,hide_index=True)

        c1,c2=st.columns(2)
        with c1:
            if st.button("👁️ Ver Dados Completos",use_container_width=True):
                st.session_state.ver_dados_completos=not st.session_state.get("ver_dados_completos",False)
        with c2:
            if st.button("🗑 Limpar e Reimportar Tudo",use_container_width=True):
                st.session_state.df_raw=None; st.session_state.projecoes={}
                if st.session_state.cid:
                    p_path=os.path.join(PASTA,f"{gid(st.session_state.cid)}_dados.csv")
                    if os.path.exists(p_path): os.remove(p_path)
                st.rerun()

        if st.session_state.get("ver_dados_completos",False):
            st.dataframe(df_ex,use_container_width=True,height=400)

# ── ERP ─────────────────────────────────────────────
elif pg=="erp":
    hdr("🔌 Integração ERP","Omie e Conta Azul")
    if not st.session_state.cid:
        st.markdown('<div class="al-w">⚠️ Selecione um cliente primeiro.</div>',unsafe_allow_html=True); st.stop()
    erp=st.radio("ERP:",["🟠 Omie","🔵 Conta Azul"],horizontal=True)
    if "Omie" in erp:
        st.markdown('<div class="al-i">📌 Omie → Configurações → API → Criar Aplicação → copie App Key e App Secret</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        ak_o=c1.text_input("App Key",type="password",key="omie_ak")
        as_o=c2.text_input("App Secret",type="password",key="omie_as")
        c3,c4,c5=st.columns(3)
        ano_o=c3.selectbox("Ano",list(range(2020,2031)),index=4)
        mes_i=c4.selectbox("Início",list(range(1,13)),format_func=lambda n:MESES[n-1])
        mes_f2=c5.selectbox("Fim",list(range(1,13)),format_func=lambda n:MESES[n-1],index=11)
        if st.button("🔍 Importar do Omie",use_container_width=True):
            dfs2=[]; errs2=[]
            pb=st.progress(0); rng=list(range(mes_i,mes_f2+1))
            with st.spinner("Buscando..."):
                for idx_m,m in enumerate(rng):
                    try:
                        ms=f"{m:02d}/{ano_o}"
                        r=requests.post("https://app.omie.com.br/api/v1/financas/dre/",
                          json={"call":"ObterRelDRE","app_key":ak_o,"app_secret":as_o,
                                "param":[{"dDtInicio":f"01/{ms}","dDtFim":f"28/{ms}"}]},timeout=30)
                        dre2=r.json(); linha={"Ano":str(ano_o),"mês":MESES[m-1]}
                        def bk(obj,k):
                            if isinstance(obj,dict):
                                if k in obj: return obj[k]
                                for v2 in obj.values():
                                    r2=bk(v2,k)
                                    if r2 is not None: return r2
                            elif isinstance(obj,list):
                                for i2 in obj:
                                    r2=bk(i2,k)
                                    if r2 is not None: return r2
                        for k2,c2_ in {"nReceitaBruta":"receita bruta de vendas",
                          "nCMV":"CMV (custo da mercadoria vendida)",
                          "nDespesasComerciais":"despesas comerciais",
                          "nDespesasAdministrativas":"despesas administrativas",
                          "nDespesasFinanceiras":"despesas financeiras líquidas"}.items():
                            v2=bk(dre2,k2)
                            if v2 is not None:
                                try: linha[c2_]=float(str(v2).replace(",","."))
                                except: pass
                        dfs2.append(linha)
                    except Exception as e: errs2.append(str(e))
                    pb.progress((idx_m+1)/len(rng))
            if dfs2:
                df_om=pd.DataFrame(dfs2); st.session_state.df_raw=df_om
                save_df(st.session_state.cid,df_om)
                st.markdown(f'<div class="al-s">✅ {len(df_om)} meses do Omie</div>',unsafe_allow_html=True)
                addlog(f"Omie: {len(df_om)} meses")
            if errs2: st.warning("; ".join(errs2[:3]))
    else:
        st.markdown('<div class="al-i">📌 Conta Azul → Integrações → API → Gerar Token</div>',unsafe_allow_html=True)
        tok=st.text_input("Access Token",type="password")
        c1,c2=st.columns(2)
        ano_ca=c1.selectbox("Ano",list(range(2020,2031)),index=4)
        mes_ca=c2.selectbox("Mês",list(range(1,13)),format_func=lambda n:MESES[n-1])
        if st.button("🔍 Importar Conta Azul",use_container_width=True):
            h={"Authorization":f"Bearer {tok}"}
            ini=f"{ano_ca}-{mes_ca:02d}-01"; fim=f"{ano_ca}-{mes_ca:02d}-28"
            linha_ca={"Ano":str(ano_ca),"mês":MESES[mes_ca-1]}
            try:
                r=requests.get("https://api.contaazul.com/v1/sales",headers=h,
                  params={"emission_start":ini,"emission_end":fim,"size":500},timeout=20)
                if r.status_code==200:
                    linha_ca["receita bruta de vendas"]=sum(float(v.get("total",0)) for v in r.json() if isinstance(v,dict))
                df_ca=pd.DataFrame([linha_ca]); st.session_state.df_raw=df_ca
                save_df(st.session_state.cid,df_ca)
                st.markdown('<div class="al-s">✅ Conta Azul importado</div>',unsafe_allow_html=True)
            except Exception as e: st.error(f"Erro: {e}")

# ── DRE ─────────────────────────────────────────────
elif pg=="dre":
    hdr("📊 DRE","Demonstração do Resultado — Real | AV% | AH%")
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df)
    anos=[str(a) for a in sorted(df[ca].dropna().unique())] if ca else []
    ano_f=st.selectbox("Filtrar por ano",["Todos"]+anos) if anos else "Todos"
    df_v=df[df[ca].astype(str)==ano_f] if ano_f!="Todos" else df
    ul=df_v.iloc[-1]
    k=st.columns(5)
    for col_k,lbl,campo,t in [(k[0],"Rec. Bruta","receita bruta de vendas","brl"),
      (k[1],"Rec. Líquida","receita líquida","brl"),(k[2],"Lucro Bruto","lucro bruto","brl"),
      (k[3],"Lucro Líquido","lucro líquido","brl"),(k[4],"EBITDA %","EBITDA %","pct")]:
        try:
            v=float(ul.get(campo,0))
            col_k.markdown(f'<div class="mc"><div class="mc-lbl">{lbl}</div>'
                          f'<div class="mc-val {cor(v)}">{fmt(v,t)}</div></div>',unsafe_allow_html=True)
        except: pass
    g1,g2=st.columns(2)
    TH_LIGHT=dict(plot_bgcolor="white",paper_bgcolor="white",
        font=dict(color="#6B7280",size=10,family="Inter"),
        xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
        yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
        margin=dict(l=8,r=8,t=36,b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))
    with g1:
        fig_rb=go.Figure()
        v=pd.to_numeric(df_v["receita bruta de vendas"],errors="coerce") if "receita bruta de vendas" in df_v.columns else pd.Series()
        x=df_v[cm].astype(str) if cm else pd.Series(range(len(df_v))).astype(str)
        cs=["#2563EB" if val>=0 else "#DC2626" for val in v]
        fig_rb.add_trace(go.Bar(x=x,y=v,marker_color=cs,
          text=[fmt(val) for val in v],textposition="outside",textfont=dict(size=8,color="#6B7280")))
        fig_rb.update_layout(title=dict(text="💰 Receita Bruta",font=dict(size=12,color="#111827")),**TH_LIGHT)
        st.plotly_chart(fig_rb,use_container_width=True)
    with g2:
        fig_mg=go.Figure()
        x=df_v[cm].astype(str) if cm else pd.Series(range(len(df_v))).astype(str)
        if ca and cm:
            x=df_v[cm].astype(str)+"/"+df_v[ca].astype(str).str[-2:]
        for c,cor_c,nm in [
          ("margem bruta %","#2563EB","Margem Bruta"),
          ("margem contrib %","#059669","Margem Contrib."),
          ("margem líquida %","#D97706","Margem Líquida"),
          ("EBITDA %","#DC2626","EBITDA")]:
            if c not in df_v.columns: continue
            fig_mg.add_trace(go.Scatter(x=x,y=pd.to_numeric(df_v[c],errors="coerce"),
              name=nm,mode="lines+markers",
              line=dict(color=cor_c,width=2.2),
              marker=dict(size=5,color=cor_c,line=dict(color="white",width=1.5)),
              hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>%{{y:.1f}}%<extra></extra>"))
        fig_mg.update_layout(title=dict(text="📊 Margens (%)",font=dict(size=12,color="#111827")),**TH_LIGHT)
        st.plotly_chart(fig_mg,use_container_width=True)
    df_12=df_v
    n=len(df_12)
    meses_cols=list(df_12[cm].astype(str)) if cm else [str(i) for i in range(n)]
    def dv(c,i):
        try: return float(df_12.iloc[i].get(c,0))
        except: return 0.
    def av(c,i):
        # AV% em relação à Receita Bruta (base = 100%)
        try: return dv(c,i)/(float(df_12.iloc[i].get("receita bruta de vendas",1)) or 1)*100
        except: return 0.
    def av_pct(c,i):
        # Para linhas que já são percentual — retorna o valor direto
        try: return float(df_12.iloc[i].get(c,0))
        except: return 0.
    def ah(c,i):
        try:
            v=dv(c,i)
            if i==0: return 0.
            v0=float(df_12.iloc[i-1].get(c,1)) or 1
            return (v-v0)/abs(v0)*100
        except:
            return 0.
    def ah_pct(c,i):
        try:
            v=float(df_12.iloc[i].get(c,0))
            if i==0: return 0.
            v0=float(df_12.iloc[i-1].get(c,0))
            return v-v0
        except:
            return 0.
    linhas=[("cat","(+) RECEITA BRUTA","receita bruta de vendas",False),
            ("sub","  Impostos s/ Vendas","impostos sobre vendas",True),
            ("sub","  Devoluções","devoluções de vendas",True),
            ("tot","= RECEITA LÍQUIDA","receita líquida",False),
            ("cat","(-) CMV","CMV (custo da mercadoria vendida)",True),
            ("tot","= LUCRO BRUTO","lucro bruto",False),
            ("pct","  Margem Bruta %","margem bruta %",False),
            ("sub","  (-) Desp. Comerciais","despesas comerciais",True),
            ("tot","= MARGEM CONTRIB.","margem contrib",False),
            ("pct","  Margem Contrib. %","margem contrib %",False),
            ("sub","  (-) Desp. Adm.","despesas administrativas",True),
            ("sub","  (-) Desp. Fin.","despesas financeiras líquidas",True),
            ("sub","  (-) Depreciação","despesas com depreciações e amortizações",True),
            ("tot","= LUCRO OPERACIONAL","lucro operacional",False),
            ("pct","  Margem Op. %","margem op %",False),
            ("sub","  (+/-) Não Operac.","receitas não operacionais",False),
            ("sub","  (-) IR/CSLL","provisão para imposto de renda",True),
            ("tot","= LUCRO LÍQUIDO","lucro líquido",False),
            ("pct","  Margem Líquida %","margem líquida %",False),
            ("tot","  EBITDA","EBITDA",False),
            ("pct","  EBITDA %","EBITDA %",False)]
    header="<tr><th>Descrição</th>"+"".join(f"<th>{m}</th><th>AV%</th><th>AH%</th>" for m in meses_cols)+"</tr>"
    rows=""
    for tipo,desc,campo,inv in linhas:
        cls_tr={"cat":"cat","tot":"tot","pct":"pct","sub":"sub"}.get(tipo,"")
        row=f'<tr class="{cls_tr}"><td>{desc}</td>'
        for i in range(n):
            if tipo=="pct":
                v=av_pct(campo,i)
                delta=ah_pct(campo,i)
                cls_d="pos" if delta>0 else ("neg" if delta<0 else "neu")
                row+=f'<td class="pct">{fmt(v,"pct")}</td>'
                row+=f'<td class="{cls_d}" style="font-size:.7rem">{"▲" if delta>0 else "▼"}{abs(delta):.1f}pp</td>'
                row+=f'<td></td>'
            else:
                v=dv(campo,i); a_v=av(campo,i); a_h=ah(campo,i)
                cls_v="neg" if (inv and v!=0) else cor(v)
                row+=f'<td class="{cls_v}">{fmt(v)}</td>'
                row+=f'<td class="{cls_pct(a_v,inv)}">{fmt(a_v,"pct")}</td>'
                row+=f'<td class="{cls_pct(a_h,inv)}">{fmt(a_h,"pct")}</td>'
        rows+=row+"</tr>"
    st.markdown(f'<div class="dre-wrap"><table class="dre">{header}{rows}</table></div>',unsafe_allow_html=True)

    # Drill-down de subcontas
    if st.session_state.cid:
        path_detalhe=os.path.join(PASTA,f"{gid(st.session_state.cid)}_detalhamento.csv")
        if os.path.exists(path_detalhe):
            df_det=pd.read_csv(path_detalhe,sep=";",decimal=",",encoding="utf-8-sig")
            campos_dre_dd=DEMONSTRACOES_CAMPOS.get("DRE",[])
            df_det_dre=df_det[df_det["campo_pai"].isin(campos_dre_dd)]
            if not df_det_dre.empty:
              with st.expander("🔍 Ver detalhamento por subconta (drill-down)"):
                campos_pai=sorted(df_det_dre["campo_pai"].unique().tolist())
                campo_sel_dd=st.selectbox("Selecione a conta",campos_pai,key="dd_campo")
                df_det_f=df_det_dre[df_det_dre["campo_pai"]==campo_sel_dd]
                if ano_f!="Todos":
                    df_det_f=df_det_f[df_det_f["ano"].astype(str)==ano_f]
                if not df_det_f.empty:
                    df_det_f=df_det_f.copy()
                    df_det_f["periodo"]=df_det_f["mes"].astype(str)+"/"+df_det_f["ano"].astype(str).str[-2:]
                    pivot=df_det_f.pivot_table(index="subconta",columns="periodo",values="valor",
                                                aggfunc="sum",fill_value=0)
                    ordem_meses=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
                    cols_ordenadas=sorted(pivot.columns,
                      key=lambda x: (x.split("/")[1], ordem_meses.index(x.split("/")[0]) if x.split("/")[0] in ordem_meses else 99))
                    pivot=pivot[cols_ordenadas]
                    pivot["Total"]=pivot.sum(axis=1)
                    pivot=pivot.sort_values("Total",ascending=False)
                    pivot_fmt=pivot.copy()
                    for c in pivot_fmt.columns:
                        pivot_fmt[c]=pivot_fmt[c].apply(lambda v: fmt(v))
                    st.dataframe(pivot_fmt,use_container_width=True)
                else:
                    st.info("Sem detalhamento disponível para esta conta no período selecionado.")

    sec("🌊 Waterfall — Último Período")
    wf_c=["receita bruta de vendas","deduções","CMV (custo da mercadoria vendida)",
          "despesas comerciais","despesas administrativas","despesas financeiras líquidas","lucro líquido"]
    wf_l=["Rec. Bruta","(-) Deduções","(-) CMV","(-) D.Com","(-) D.Adm","(-) D.Fin","= Luc. Líq."]
    wf_v=[float(ul.get(c,0)) for c in wf_c]
    if any(v!=0 for v in wf_v):
        fig_wf=go.Figure(go.Waterfall(orientation="v",measure=["relative"]*len(wf_l),x=wf_l,y=wf_v,
          connector=dict(line=dict(color="#E8ECF0",width=1)),
          increasing=dict(marker=dict(color="#059669")),
          decreasing=dict(marker=dict(color="#DC2626")),
          totals=dict(marker=dict(color="#2563EB")),
          text=[fmt(v) for v in wf_v],textposition="outside",
          textfont=dict(size=9,color="#6B7280")))
        fig_wf.update_layout(
          title=dict(text="🌊 Composição do Resultado — Último Período",
                     font=dict(size=12,color="#111827")),
          plot_bgcolor="white",paper_bgcolor="white",
          font=dict(color="#6B7280",size=10,family="Inter"),
          margin=dict(l=8,r=8,t=44,b=8),
          xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False),
          yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
          showlegend=False)
        st.plotly_chart(fig_wf,use_container_width=True)

# ── FLUXO ───────────────────────────────────────────
elif pg=="fluxo":
    hdr("💰 Fluxo de Caixa","Entradas, saídas, saldo e alertas automáticos")
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df); si=st.session_state.saldo_ini

    # Filtros
    col_f1,col_f2=st.columns(2)
    anos_disp=["Todos"]+[str(a) for a in sorted(df[ca].dropna().unique().tolist())] if ca else ["Todos"]
    ano_sel=col_f1.selectbox("Ano",anos_disp,key="fluxo_ano")
    df=df[df[ca].astype(str)==ano_sel].reset_index(drop=True) if ano_sel!="Todos" else df.reset_index(drop=True)
    meses_disp=["Todos"]+df[cm].dropna().unique().tolist() if cm else ["Todos"]
    mes_sel=col_f2.selectbox("Mês",meses_disp,key="fluxo_mes")
    df=df[df[cm]==mes_sel].reset_index(drop=True) if mes_sel!="Todos" else df.reset_index(drop=True)
    if df.empty: st.warning("Sem dados para este período."); st.stop()
    df_f=df.copy()
    ent=pd.to_numeric(df_f.get("Disponibilidades entradas",pd.Series(0,index=df_f.index)),errors="coerce").fillna(0)
    sai=pd.to_numeric(df_f.get("Disponibilidades Saida",pd.Series(0,index=df_f.index)),errors="coerce").fillna(0)
    ev=float(st.session_state.get("entradas_vista",0))
    freq=st.session_state.get("freq_fluxo","Mensal")
    if ev>0:
        ent_vista=pd.Series([ev*22 if freq=="Diário" else ev]*len(df_f),index=df_f.index)
        df_f["entradas à vista"]=ent_vista
        ent=ent+ent_vista
    df_f["tot entradas"]=ent; df_f["tot saidas"]=sai
    df_f["saldo período"]=ent-sai; df_f["saldo acumulado"]=si+(ent-sai).cumsum()
    ul=df_f.iloc[-1]
    k=st.columns(4)
    mc(k[0],"Saldo Inicial",fmt(si),"b")
    mc(k[1],"Total Entradas",fmt(ent.sum()),"g",f"Média: {fmt(ent.mean())}/mês")
    mc(k[2],"Total Saídas",fmt(sai.sum()),"r",f"Média: {fmt(sai.mean())}/mês")
    sf=float(ul.get("saldo acumulado",si)); mc(k[3],"Saldo Final",fmt(sf),cor(sf))
    sec("🚨 Alertas de Caixa")
    neg=df_f[df_f["saldo acumulado"]<0]
    if len(neg)>0:
        mn=neg[cm].tolist() if cm else list(neg.index)
        st.markdown(f'<div class="al-d">🔴 Caixa NEGATIVO em <b>{len(neg)}</b> período(s): {", ".join(str(m) for m in mn)}<br>Ação: negociar prazos com fornecedores ou antecipar recebíveis.</div>',unsafe_allow_html=True)
    elif len(df_f[df_f["saldo acumulado"]<df_f["saldo acumulado"].mean()*.3])>0:
        st.markdown('<div class="al-w">⚠️ Caixa abaixo de 30% da média em alguns períodos.</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="al-s">✅ Caixa positivo em todos os períodos.</div>',unsafe_allow_html=True)
    sec("📈 Evolução")
    g1,g2=st.columns(2)
    x=df_f[cm].astype(str) if cm else pd.Series(range(len(df_f))).astype(str)
    if ca and cm:
        x=df_f[cm].astype(str)+"/"+df_f[ca].astype(str).str[-2:]
    TH_FC=dict(plot_bgcolor="white",paper_bgcolor="white",
        font=dict(color="#6B7280",size=10,family="Inter"),
        xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
        yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
        margin=dict(l=8,r=8,t=40,b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))
    with g1:
        fig_fc=go.Figure()
        fig_fc.add_trace(go.Bar(x=x,y=df_f["tot entradas"],name="Entradas",
          marker_color="#059669",opacity=.85,
          hovertemplate="<b>Entradas</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>"))
        fig_fc.add_trace(go.Bar(x=x,y=-df_f["tot saidas"],name="Saídas",
          marker_color="#DC2626",opacity=.85,
          hovertemplate="<b>Saídas</b><br>%{x}<br>R$ %{customdata:,.0f}<extra></extra>",
          customdata=df_f["tot saidas"]))
        fig_fc.update_layout(title=dict(text="💰 Entradas vs Saídas",
          font=dict(size=12,color="#111827")),barmode="relative",**TH_FC)
        st.plotly_chart(fig_fc,use_container_width=True)
    with g2:
        saldo=df_f["saldo acumulado"]
        cor_saldo="#059669" if float(saldo.iloc[-1])>=0 else "#DC2626"
        fig_sal=go.Figure()
        fig_sal.add_trace(go.Scatter(x=x,y=saldo,fill="tozeroy",mode="lines+markers",
          line=dict(color=cor_saldo,width=2.5),
          fillcolor="rgba(5,150,105,.07)" if cor_saldo=="#059669" else "rgba(220,38,38,.07)",
          marker=dict(size=5,color=cor_saldo,line=dict(color="white",width=1.5)),
          hovertemplate="<b>Saldo</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>"))
        fig_sal.add_hline(y=0,line_dash="dash",line_color="#DC2626",opacity=0.3)
        fig_sal.update_layout(title=dict(text="📈 Saldo Acumulado",
          font=dict(size=12,color="#111827")),**TH_FC,showlegend=False)
        st.plotly_chart(fig_sal,use_container_width=True)
    sec("📊 Detalhamento")
    t1,t2=st.tabs(["Entradas por tipo","Saídas por Centro"])
    cc_ent=[c for c in CAMPOS_FLUXO if "Entradas" in c and c!="Disponibilidades entradas" and c in df_f.columns]
    cc_sai=[c for c in CAMPOS_FLUXO if "Saidas" in c and c in df_f.columns]
    nomes_band={"Centro de Custos Entradas 1":"Receita Serviços","Centro de Custos Entradas 2":"Receita Produtos",
               "Centro de Custos Entradas 3":"Recebimento Clientes","Centro de Custos Entradas 4":"Receita Financeira/Outras"}
    CORES_LIGHT=["#2563EB","#059669","#D97706","#DC2626","#7C3AED","#0891B2"]
    with t1:
        fig_ent=go.Figure()
        totais_ent={}
        # Bandeiras
        if cc_ent:
            for i,c in enumerate(cc_ent):
                nome=nomes_band.get(c,c)
                vals=pd.to_numeric(df_f[c],errors="coerce").fillna(0)
                fig_ent.add_trace(go.Bar(x=x,y=vals,name=nome,
                  marker_color=CORES_LIGHT[i%len(CORES_LIGHT)],opacity=.85))
                totais_ent[nome]=float(vals.sum())
        # Entradas à Vista
        ev=float(st.session_state.get("entradas_vista",0))
        freq=st.session_state.get("freq_fluxo","Mensal")
        if ev>0:
            vals_vista=pd.Series([ev*22 if freq=="Diário" else ev]*len(df_f),index=df_f.index)
            fig_ent.add_trace(go.Bar(x=x,y=vals_vista,name="À Vista",
              marker_color="#0891B2",opacity=.85))
            totais_ent["À Vista"]=float(vals_vista.sum())
        if fig_ent.data:
            fig_ent.update_layout(title=dict(text="💰 Entradas por Categoria",
              font=dict(size=12,color="#111827")),barmode="stack",**TH_FC)
            st.plotly_chart(fig_ent,use_container_width=True)
            # Pizza com todas as categorias
            if totais_ent:
                fig_pie=go.Figure(go.Pie(
                  labels=list(totais_ent.keys()),
                  values=list(totais_ent.values()),
                  marker=dict(colors=CORES_LIGHT[:len(totais_ent)]),
                  hole=.45,textfont=dict(size=10,color="#111827")))
                fig_pie.update_layout(
                  title=dict(text="Distribuição das Entradas",font=dict(size=12,color="#111827")),
                  plot_bgcolor="white",paper_bgcolor="white",
                  font=dict(color="#6B7280",size=10),
                  margin=dict(l=8,r=8,t=40,b=8),height=280,
                  legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=9)))
                st.plotly_chart(fig_pie,use_container_width=True)
        else:
            st.markdown('<div class="al-i">Dados de entradas não disponíveis neste arquivo.</div>',unsafe_allow_html=True)
    with t2:
        nomes_sai={"Centro de Custos Saidas 1":"Folha","Centro de Custos Saidas 2":"Fornecedores",
                  "Centro de Custos Saidas 3":"Impostos/Operacionais","Centro de Custos Saidas 4":"Investimentos"}
        if cc_sai:
            fig_sai=go.Figure()
            for i,c in enumerate(cc_sai):
                fig_sai.add_trace(go.Bar(x=x,
                  y=pd.to_numeric(df_f[c],errors="coerce").fillna(0),
                  name=nomes_sai.get(c,c),
                  marker_color=CORES_LIGHT[i%len(CORES_LIGHT)],opacity=.85))
            fig_sai.update_layout(title=dict(text="📦 Saídas por Centro de Custo",
              font=dict(size=12,color="#111827")),
              barmode="stack",**TH_FC)
            st.plotly_chart(fig_sai,use_container_width=True)
        else:
            st.markdown('<div class="al-i">Dados de centro de custo não disponíveis.</div>',unsafe_allow_html=True)

    if st.session_state.cid:
        path_detalhe_fc=os.path.join(PASTA,f"{gid(st.session_state.cid)}_detalhamento.csv")
        if os.path.exists(path_detalhe_fc):
            df_det_fc=pd.read_csv(path_detalhe_fc,sep=";",decimal=",",encoding="utf-8-sig")
            df_det_fc_fluxo=df_det_fc[df_det_fc["campo_pai"].isin(["Disponibilidades entradas","Disponibilidades Saida"])]
            if not df_det_fc_fluxo.empty:
                with st.expander("🔍 Ver detalhamento por categoria (drill-down)"):
                    campos_pai_fc=sorted(df_det_fc_fluxo["campo_pai"].unique().tolist())
                    campo_sel_fc=st.selectbox("Selecione",campos_pai_fc,key="dd_fluxo_campo",
                      format_func=lambda x: "Entradas" if x=="Disponibilidades entradas" else "Saídas")
                    df_det_f_fc=df_det_fc_fluxo[df_det_fc_fluxo["campo_pai"]==campo_sel_fc]
                    if ano_sel!="Todos":
                        df_det_f_fc=df_det_f_fc[df_det_f_fc["ano"].astype(str)==ano_sel]
                    if mes_sel!="Todos":
                        mes_sel_3=str(mes_sel).lower()[:3]
                        df_det_f_fc=df_det_f_fc[df_det_f_fc["mes"].astype(str).str.lower()==mes_sel_3]
                    if not df_det_f_fc.empty:
                        df_det_f_fc=df_det_f_fc.copy()
                        df_det_f_fc["periodo"]=df_det_f_fc["mes"].astype(str)+"/"+df_det_f_fc["ano"].astype(str).str[-2:]
                        pivot_fc=df_det_f_fc.pivot_table(index="subconta",columns="periodo",values="valor",
                                                        aggfunc="sum",fill_value=0)
                        ordem_meses_fc=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
                        cols_ordenadas_fc=sorted(pivot_fc.columns,
                          key=lambda x: (x.split("/")[1], ordem_meses_fc.index(x.split("/")[0]) if x.split("/")[0] in ordem_meses_fc else 99))
                        pivot_fc=pivot_fc[cols_ordenadas_fc]
                        pivot_fc["Total"]=pivot_fc.sum(axis=1)
                        pivot_fc=pivot_fc.sort_values("Total",ascending=False)
                        pivot_fc_fmt=pivot_fc.copy()
                        for c in pivot_fc_fmt.columns:
                            pivot_fc_fmt[c]=pivot_fc_fmt[c].apply(lambda v: fmt(v))
                        st.dataframe(pivot_fc_fmt,use_container_width=True)
                    else:
                        st.info("Sem detalhamento disponível para este período.")

    sec("📋 Tabela Completa")
    cols_show=[c for c in [cm,"tot entradas","tot saidas","saldo período","saldo acumulado"] if c and c in df_f.columns]
    st.dataframe(df_f[cols_show] if cols_show else df_f,use_container_width=True)

# ── BALANÇO ─────────────────────────────────────────
elif pg=="balanco":
    hdr("🏦 Balanço Patrimonial","Posição financeira com AV% e AH%")
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df)
    anos=[str(a) for a in sorted(df[ca].dropna().unique())] if ca else []
    col_b1,col_b2=st.columns(2)
    ano_b=col_b1.selectbox("Ano",["Todos"]+anos,key="bal_ano")
    df_b=df[df[ca].astype(str)==ano_b].reset_index(drop=True) if ano_b!="Todos" else df.reset_index(drop=True)
    meses_b=["Todos"]+df_b[cm].dropna().unique().tolist() if cm else ["Todos"]
    mes_b=col_b2.selectbox("Mês",meses_b,key="bal_mes")
    df_b=df_b[df_b[cm]==mes_b].reset_index(drop=True) if mes_b!="Todos" else df_b
    if df_b.empty: st.warning("Sem dados para este período."); st.stop()
    df_b4=df_b  # todos os períodos filtrados
    ul=df_b4.iloc[-1]
    k=st.columns(4)
    mc(k[0],"Ativo Total",fmt(ul.get("ativo total",0)),"b")
    mc(k[1],"Passivo Total",fmt(ul.get("pass total",0)),"r")
    mc(k[2],"Patrimônio Líquido",fmt(ul.get("PL",0)),cor(ul.get("PL",0)))
    li=float(ul.get("liquidez imediata",0) or 0)
    mc(k[3],"Liq. Imediata",fmt(li,"x"),"g" if li>=0.5 else ("y" if li>=0.3 else "r"),
       "✅ Saudável" if li>=0.5 else ("⚠️ Atenção" if li>=0.3 else "🔴 Risco"))
    x_b=list(df_b4[cm].astype(str)) if cm else [str(i) for i in range(len(df_b4))]
    sec("📋 Balanço — Real | AV% | AH%")
    def bal_row(desc,campo,tipo="sub",inv=False):
        row=f'<tr class="{tipo}"><td>{desc}</td>'
        for i in range(len(df_b4)):
            v=float(df_b4.iloc[i].get(campo,0))
            # AV% usa Ativo Total do mesmo período como base
            at_i=float(df_b4.iloc[i].get("ativo total",1) or 1)
            a_v=v/at_i*100
            a_h=safe(v-float(df_b4.iloc[i-1].get(campo,1)),
                     abs(float(df_b4.iloc[i-1].get(campo,1)) or 1))*100 if i>0 else 0.
            row+=f'<td class="{cor(v,inv)}">{fmt(v)}</td>'
            row+=f'<td class="{cls_pct(a_v,inv)}">{fmt(a_v,"pct")}</td>'
            row+=f'<td class="{cls_pct(a_h,inv)}">{fmt(a_h,"pct")}</td>'
        return row+"</tr>"
    header_b="<tr><th>Descrição</th>"+"".join(f"<th>{m}</th><th>AV%</th><th>AH%</th>" for m in x_b)+"</tr>"
    def tot_row(desc,campo,cls="b"):
        row=f'<tr class="tot"><td>{desc}</td>'
        for i in range(len(df_b4)):
            v=float(df_b4.iloc[i].get(campo,0))
            at_i=float(df_b4.iloc[i].get("ativo total",1) or 1)
            a_v=v/at_i*100
            a_h=safe(v-float(df_b4.iloc[i-1].get(campo,1)),
                     abs(float(df_b4.iloc[i-1].get(campo,1)) or 1))*100 if i>0 else 0.
            row+=f'<td class="{cls}">{fmt(v)}</td>'
            row+=f'<td>{fmt(a_v,"pct")}</td>'
            row+=f'<td class="{cls_pct(a_h)}">{fmt(a_h,"pct")}</td>'
        return row+"</tr>"
    rows_b=('<tr class="cat"><td>ATIVO</td>'+"".join("<td></td><td></td><td></td>" for _ in x_b)+"</tr>"+
        bal_row("  Disponibilidades","disponibilidades saldo")+
        bal_row("  Contas a Receber","contas a receber saldo")+
        bal_row("  Estoques","estoque final do mês de mercadorias para revenda saldo")+
        bal_row("  Outros AC","Outros AC")+
        tot_row("= ATIVO CIRCULANTE","ativo circ")+
        bal_row("  Ativo NC","Ativo NC")+
        tot_row("= ATIVO TOTAL","ativo total")+
        '<tr class="cat"><td>PASSIVO</td>'+"".join("<td></td><td></td><td></td>" for _ in x_b)+"</tr>"+
        bal_row("  Fornecedores","contas a pagar de fornecedores saldo",inv=True)+
        bal_row("  Pass. Financeiros","Passivos Financeiros",inv=True)+
        bal_row("  Outros PC","Outros PC",inv=True)+
        tot_row("= PASSIVO CIRCULANTE","pass circ","r")+
        bal_row("  Passivo NC","Passivo NC",inv=True)+
        tot_row("= PASSIVO TOTAL","pass total","r")+
        tot_row("= PATRIMÔNIO LÍQUIDO","PL","g"))
    st.markdown(f'<div class="dre-wrap" style="overflow-x:auto;max-width:100%"><table class="dre" style="min-width:1200px">{header_b}{rows_b}</table></div>',unsafe_allow_html=True)

    if st.session_state.cid:
        path_detalhe_bal=os.path.join(PASTA,f"{gid(st.session_state.cid)}_detalhamento.csv")
        if os.path.exists(path_detalhe_bal):
            df_det_bal=pd.read_csv(path_detalhe_bal,sep=";",decimal=",",encoding="utf-8-sig")
            campos_balanco_dd=["disponibilidades saldo","contas a receber saldo",
                "estoque final do mês de mercadorias para revenda saldo","Outros AC","Ativo NC",
                "contas a pagar de fornecedores saldo","Passivos Financeiros","Outros PC","Passivo NC","PL"]
            df_det_bal_f=df_det_bal[df_det_bal["campo_pai"].isin(campos_balanco_dd)]
            if not df_det_bal_f.empty:
                with st.expander("🔍 Ver detalhamento por subconta (drill-down)"):
                    campos_pai_bal=sorted(df_det_bal_f["campo_pai"].unique().tolist())
                    campo_sel_bal=st.selectbox("Selecione a conta",campos_pai_bal,key="dd_bal_campo")
                    df_det_bal_sel=df_det_bal_f[df_det_bal_f["campo_pai"]==campo_sel_bal]
                    if ano_b!="Todos":
                        df_det_bal_sel=df_det_bal_sel[df_det_bal_sel["ano"].astype(str)==ano_b]
                    if mes_b!="Todos":
                        mes_b_3=str(mes_b).lower()[:3]
                        df_det_bal_sel=df_det_bal_sel[df_det_bal_sel["mes"].astype(str).str.lower()==mes_b_3]
                    if not df_det_bal_sel.empty:
                        df_det_bal_sel=df_det_bal_sel.copy()
                        df_det_bal_sel["periodo"]=df_det_bal_sel["mes"].astype(str)+"/"+df_det_bal_sel["ano"].astype(str).str[-2:]
                        pivot_bal=df_det_bal_sel.pivot_table(index="subconta",columns="periodo",values="valor",
                                                            aggfunc="sum",fill_value=0)
                        ordem_meses_bal=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
                        cols_ordenadas_bal=sorted(pivot_bal.columns,
                          key=lambda x: (x.split("/")[1], ordem_meses_bal.index(x.split("/")[0]) if x.split("/")[0] in ordem_meses_bal else 99))
                        pivot_bal=pivot_bal[cols_ordenadas_bal]
                        pivot_bal_fmt=pivot_bal.copy()
                        for c in pivot_bal_fmt.columns:
                            pivot_bal_fmt[c]=pivot_bal_fmt[c].apply(lambda v: fmt(v))
                        st.dataframe(pivot_bal_fmt,use_container_width=True)
                    else:
                        st.info("Sem detalhamento disponível para esta conta no período selecionado.")

    g1,g2=st.columns(2)
    TH_BAL=dict(plot_bgcolor="white",paper_bgcolor="white",
        font=dict(color="#6B7280",size=10,family="Inter"),
        xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
        yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
        margin=dict(l=8,r=8,t=40,b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))
    x_bal=df[cm].astype(str) if cm else pd.Series(range(len(df))).astype(str)
    if ca and cm:
        x_bal=df[cm].astype(str)+"/"+df[ca].astype(str).str[-2:]
    with g1:
        fig_pat=go.Figure()
        for c,cor_c,nm in [("ativo total","#2563EB","Ativo Total"),
                            ("pass total","#DC2626","Passivo Total"),
                            ("PL","#059669","Patrimônio Líquido")]:
            if c not in df.columns: continue
            fig_pat.add_trace(go.Scatter(x=x_bal,y=pd.to_numeric(df[c],errors="coerce"),
              name=nm,mode="lines+markers",line=dict(color=cor_c,width=2.2),
              marker=dict(size=5,color=cor_c,line=dict(color="white",width=1.5)),
              hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>R$ %{{y:,.0f}}<extra></extra>"))
        fig_pat.update_layout(title=dict(text="🏛️ Estrutura Patrimonial",
          font=dict(size=12,color="#111827")),**TH_BAL)
        st.plotly_chart(fig_pat,use_container_width=True)
    with g2:
        fig_liq=go.Figure()
        for c,cor_c,nm,ref in [("liquidez corrente","#2563EB","Liq. Corrente",1.5),
                                ("liquidez imediata","#059669","Liq. Imediata",0.5)]:
            if c not in df.columns: continue
            fig_liq.add_trace(go.Scatter(x=x_bal,y=pd.to_numeric(df[c],errors="coerce"),
              name=nm,mode="lines+markers",line=dict(color=cor_c,width=2.2),
              marker=dict(size=5,color=cor_c,line=dict(color="white",width=1.5)),
              hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>%{{y:.2f}}x<extra></extra>"))
            fig_liq.add_hline(y=ref,line_dash="dash",line_color=cor_c,opacity=0.25)
        fig_liq.update_layout(title=dict(text="💧 Índices de Liquidez",
          font=dict(size=12,color="#111827")),**TH_BAL)
        st.plotly_chart(fig_liq,use_container_width=True)

    with st.expander("🔮 Ver projeção dos próximos 12 meses — Balanço"):
        if len(df)<6:
            st.markdown('<div class="al-w">⚠️ Mínimo 6 períodos para gerar projeções.</div>',unsafe_allow_html=True)
        else:
            mds=[m for m,ok in MODELOS_ML.items() if ok]
            x_h=df[cm].astype(str) if cm else pd.Series(range(len(df))).astype(str)
            if ca and cm:
                x_h=df[cm].astype(str)+"/"+df[ca].astype(str).str[-2:]
            x_p=[f"M+{i+1}" for i in range(12)]

            def graf_proj_bal(campos_cores, titulo):
                fig=go.Figure()
                for campo,cor_c,nm in campos_cores:
                    if campo not in df.columns: continue
                    # Histórico
                    v_hist=pd.to_numeric(df[campo],errors="coerce")
                    fig.add_trace(go.Scatter(x=x_h,y=v_hist,name=f"{nm} (hist.)",
                      mode="lines+markers",line=dict(color=cor_c,width=2.2),
                      marker=dict(size=4,color=cor_c,line=dict(color="white",width=1.5)),
                      hovertemplate=f"<b>{nm}</b><br>%{{x}}<br>%{{y:,.2f}}<extra></extra>"))
                    # Projeção
                    try:
                        melhor_g,_=melhor_modelo(df[campo],mds)
                        proj_g=treinar(df[campo],melhor_g,12)
                        if proj_g is not None:
                            fig.add_trace(go.Scatter(x=x_p,y=proj_g.values,
                              name=f"{nm} (proj. {melhor_g})",
                              mode="lines+markers",
                              line=dict(color=cor_c,width=2,dash="dash"),
                              marker=dict(size=5,color=cor_c,symbol="diamond",
                                          line=dict(color="white",width=1.5)),
                              hovertemplate=f"<b>{nm} proj.</b><br>%{{x}}<br>%{{y:,.2f}}<extra></extra>"))
                            # Banda ±15%
                            y_up=[v*1.15 for v in proj_g.values]
                            y_dn=[v*0.85 for v in proj_g.values]
                            fig.add_trace(go.Scatter(
                              x=list(x_p)+list(x_p)[::-1],y=y_up+y_dn[::-1],
                              fill="toself",fillcolor=f"rgba(0,0,0,.03)",
                              line=dict(color="rgba(0,0,0,0)"),
                              showlegend=False))
                    except: pass
                fig.update_layout(
                  title=dict(text=titulo,font=dict(size=12,color="#111827")),
                  plot_bgcolor="white",paper_bgcolor="white",
                  font=dict(color="#6B7280",size=10),
                  margin=dict(l=8,r=8,t=44,b=40),
                  xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
                  yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
                  legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.35,font=dict(size=9)),
                  hovermode="x unified",
                  hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))
                return fig

            gb1,gb2=st.columns(2)
            with gb1:
                fig_pp=graf_proj_bal([
                  ("ativo total","#2563EB","Ativo Total"),
                  ("pass total","#DC2626","Passivo Total"),
                  ("PL","#059669","Patrimônio Líquido")],
                  "🏛️ Projeção — Estrutura Patrimonial")
                st.plotly_chart(fig_pp,use_container_width=True)
            with gb2:
                fig_lp=graf_proj_bal([
                  ("liquidez corrente","#2563EB","Liq. Corrente"),
                  ("liquidez imediata","#059669","Liq. Imediata")],
                  "💧 Projeção — Índices de Liquidez")
                st.plotly_chart(fig_lp,use_container_width=True)

# ── INDICADORES ─────────────────────────────────────
elif pg=="indicadores":
    hdr("📈 Indicadores","KPIs com gauge, histórico, máx. e mín.")
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df)

    # Filtros
    col_i1,col_i2=st.columns(2)
    anos_i=["Todos"]+[str(a) for a in sorted(df[ca].dropna().unique().tolist())] if ca else ["Todos"]
    ano_i=col_i1.selectbox("Ano",anos_i,key="ind_ano")
    df_i=df[df[ca].astype(str)==ano_i].reset_index(drop=True) if ano_i!="Todos" else df.reset_index(drop=True)
    meses_i=["Todos"]+df_i[cm].dropna().unique().tolist() if cm else ["Todos"]
    mes_i=col_i2.selectbox("Mês",meses_i,key="ind_mes")
    df_i=df_i[df_i[cm]==mes_i].reset_index(drop=True) if mes_i!="Todos" else df_i
    if df_i.empty: st.warning("Sem dados para este período."); st.stop()
    ul=df_i.iloc[-1]
    sec("🌡️ Termômetro de Kanitz")
    try:
        k_v=float(ul.get("kanitz",0))
        if k_v>0: st.markdown(f'<div class="kz-s"><b style="color:#00D4AA">✅ SOLVENTE — {k_v:.2f}</b> &nbsp; Acima de 0: boa saúde financeira.</div>',unsafe_allow_html=True)
        elif k_v>=-3: st.markdown(f'<div class="kz-w"><b style="color:#FFB627">⚠️ PENUMBRA — {k_v:.2f}</b> &nbsp; Entre -3 e 0: atenção necessária.</div>',unsafe_allow_html=True)
        else: st.markdown(f'<div class="kz-d"><b style="color:#F85149">🔴 INSOLVENTE — {k_v:.2f}</b> &nbsp; Abaixo de -3: alto risco.</div>',unsafe_allow_html=True)
    except: pass
    sec("📊 Gauges")
    g1,g2,g3,g4=st.columns(4)
    try: g1.plotly_chart(gauge(float(ul.get("margem líquida %",0)),"Margem Líquida %",-20,50,"#2176FF"),use_container_width=True)
    except: pass
    try: g2.plotly_chart(gauge(float(ul.get("EBITDA %",0)),"EBITDA %",-10,60,"#00D4AA"),use_container_width=True)
    except: pass
    try:
        lc2=float(ul.get("liquidez corrente",0) or 0)
        g3.plotly_chart(gauge(min(lc2,3),"Liquidez Corrente",0,3,"#00D4AA" if lc2>=1.5 else ("#FFB627" if lc2>=1 else "#F85149")),use_container_width=True)
    except: pass
    try:
        k_v2=float(ul.get("kanitz",0))
        g4.plotly_chart(gauge(max(min(k_v2,15),-7),"Kanitz",-7,15,"#00D4AA" if k_v2>0 else ("#FFB627" if k_v2>=-3 else "#F85149")),use_container_width=True)
    except: pass
    sec("📋 Todos os Indicadores")
    inds=[("Lucratividade","margem líquida %","pct",False),("Margem EBITDA","EBITDA %","pct",False),
          ("Margem Bruta","margem bruta %","pct",False),("Margem Contrib.","margem contrib %","pct",False),
          ("ROE","ROE","pct",False),("ICD","ICD","pct",False),
          ("Liq. Corrente","liquidez corrente","x",False),("Liq. Imediata","liquidez imediata","x",False),
          ("PMR (dias)","PMR","d",True),("PMP (dias)","PMP","d",False),
          ("PME (dias)","PME","d",True),("Ciclo Caixa","ciclo de caixa","d",True),
          ("Giro Estoque","giro estoque","x",False),("Ticket Médio","ticket médio","brl",False),
          ("Lucro Líquido","lucro líquido","brl",False),("EBITDA R$","EBITDA","brl",False)]
    cols_ind=st.columns(4)
    for i,(lbl,campo,t,inv) in enumerate(inds):
        try:
            v=float(ul.get(campo,0) or 0)
            mx_v=float(df_i[campo].max() or 0) if campo in df_i.columns else 0
            mn_v=float(df_i[campo].min() or 0) if campo in df_i.columns else 0
            cols_ind[i%4].markdown(
                f'<div class="mc"><div class="mc-lbl">{lbl}</div>'
                f'<div class="mc-val {cor(v,inv)}">{fmt(v,t)}</div>'
                f'<div class="mc-sub">Max: {fmt(mx_v,t)} | Min: {fmt(mn_v,t)}</div></div>',unsafe_allow_html=True)
        except: pass
    sec("📈 Evolução")
    t1,t2,t3,t4=st.tabs(["Margens","Liquidez","Prazos","ROE / ICD"])
    TH_IND=dict(plot_bgcolor="white",paper_bgcolor="white",
        font=dict(color="#6B7280",size=10,family="Inter"),
        xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
        yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
        margin=dict(l=8,r=8,t=40,b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))

    def gl_light(df,campos,titulo,cx=None):
        fig=go.Figure()
        cores_l=["#2563EB","#059669","#D97706","#DC2626","#7C3AED"]
        x=df[cx] if cx and cx in df.columns else df.index
        if ca and cm and cx==cm:
            x=df[cm].astype(str)+"/"+df[ca].astype(str).str[-2:]
        for i,c in enumerate(campos):
            if c not in df.columns: continue
            fig.add_trace(go.Scatter(x=x,y=pd.to_numeric(df[c],errors="coerce"),
              name=c,mode="lines+markers",
              line=dict(color=cores_l[i%len(cores_l)],width=2.2),
              marker=dict(size=5,color=cores_l[i%len(cores_l)],
                          line=dict(color="white",width=1.5))))
        fig.update_layout(title=dict(text=titulo,font=dict(size=12,color="#111827")),**TH_IND)
        return fig

    with t1: st.plotly_chart(gl_light(df_i,["margem bruta %","margem contrib %","margem op %","margem líquida %","EBITDA %"],"Margens %",cm),use_container_width=True)
    with t2: st.plotly_chart(gl_light(df_i,["liquidez corrente","liquidez imediata"],"Liquidez",cm),use_container_width=True)
    with t3: st.plotly_chart(gl_light(df_i,["PMR","PMP","PME","ciclo de caixa"],"Prazos (dias)",cm),use_container_width=True)
    with t4: st.plotly_chart(gl_light(df_i,["ROE","ICD"],"ROE e ICD %",cm),use_container_width=True)

# ── ALERTAS ─────────────────────────────────────────
elif pg=="alertas":
    hdr("🚨 Alertas e Diagnóstico","Análise automática da saúde financeira por período")
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df)

    # Filtros
    col_a1,col_a2=st.columns(2)
    anos_a=["Todos"]+[str(a) for a in sorted(df[ca].dropna().unique().tolist())] if ca else ["Todos"]
    ano_a=col_a1.selectbox("Ano",anos_a,key="al_ano")
    df_a=df[df[ca].astype(str)==ano_a].reset_index(drop=True) if ano_a!="Todos" else df.reset_index(drop=True)
    meses_a=["Todos"]+df_a[cm].dropna().unique().tolist() if cm else ["Todos"]
    mes_a=col_a2.selectbox("Mês",meses_a,key="al_mes")
    df_a=df_a[df_a[cm]==mes_a].reset_index(drop=True) if mes_a!="Todos" else df_a
    if df_a.empty: st.warning("Sem dados para este período."); st.stop()
    ul=df_a.iloc[-1]
    periodo_a=f"{ul.get(cm,'')} {ul.get(ca,'')}".strip()

    # Score
    sc=float(ul.get("score_risco",50)); lbl,cls_s,cor_s=score_label(sc)
    cor_num="#059669" if sc>=80 else ("#D97706" if sc>=60 else ("#EA580C" if sc>=40 else "#DC2626"))

    sec(f"🎯 Score de Saúde — {periodo_a}")
    c1,c2,c3,c4=st.columns(4)
    mc(c1,"Score",f"{sc:.0f}/100","g" if sc>=80 else ("y" if sc>=60 else "r"))

    # Alertas automáticos
    alertas=[]
    def chk(tipo,msg,detalhe=""): alertas.append((tipo,msg,detalhe))

    try:
        ml=float(ul.get("margem líquida %",0))
        if ml<0: chk("d","💸 Prejuízo operacional",f"Margem Líquida: {ml:.1f}% — empresa gastando mais do que fatura")
        elif ml<5: chk("w","⚠️ Margem Líquida muito baixa",f"{ml:.1f}% — mínimo recomendado é 5%")
        else: chk("s","✅ Margem Líquida saudável",f"{ml:.1f}%")
    except: pass
    try:
        mb=float(ul.get("margem bruta %",0))
        if mb<20: chk("w","⚠️ Margem Bruta baixa",f"{mb:.1f}% — revisar CMV e precificação")
        else: chk("s","✅ Margem Bruta adequada",f"{mb:.1f}%")
    except: pass
    try:
        lc=float(ul.get("liquidez corrente",0) or 0)
        if lc<1: chk("d","🔴 Liquidez Corrente crítica",f"{lc:.2f}x — dívidas de curto prazo maiores que ativos circulantes")
        elif lc<1.5: chk("w","⚠️ Liquidez Corrente abaixo do ideal",f"{lc:.2f}x — recomendado ≥ 1,5x")
        else: chk("s","✅ Liquidez Corrente saudável",f"{lc:.2f}x")
    except: pass
    try:
        li=float(ul.get("liquidez imediata",0) or 0)
        if li<0.3: chk("d","🔴 Liquidez Imediata crítica",f"{li:.2f}x — caixa insuficiente para cobrir dívidas imediatas")
        elif li<0.5: chk("w","⚠️ Liquidez Imediata baixa",f"{li:.2f}x — recomendado ≥ 0,5x")
        else: chk("s","✅ Liquidez Imediata saudável",f"{li:.2f}x")
    except: pass
    try:
        kz=float(ul.get("kanitz",0))
        if kz<-3: chk("d","🔴 Kanitz — Zona Insolvente",f"{kz:.2f} — alto risco de insolvência")
        elif kz<0: chk("w","⚠️ Kanitz — Zona de Penumbra",f"{kz:.2f} — situação financeira incerta")
        else: chk("s","✅ Kanitz — Zona Solvente",f"{kz:.2f} — empresa financeiramente saudável")
    except: pass
    try:
        cc=float(ul.get("ciclo de caixa",0) or 0)
        if cc>90: chk("d","🔴 Ciclo de Caixa muito elevado",f"{cc:.0f} dias — capital de giro muito comprometido")
        elif cc>60: chk("w","⚠️ Ciclo de Caixa elevado",f"{cc:.0f} dias — monitorar capital de giro")
        elif cc<0: chk("s","✅ Ciclo de Caixa negativo (favorável)",f"{cc:.0f} dias — empresa recebe antes de pagar")
        else: chk("s","✅ Ciclo de Caixa adequado",f"{cc:.0f} dias")
    except: pass
    try:
        roe=float(ul.get("ROE",0))
        if roe<0: chk("d","💸 ROE negativo",f"{roe:.1f}% — retorno negativo sobre patrimônio")
        elif roe<6: chk("w","⚠️ ROE baixo",f"{roe:.1f}% — abaixo da taxa mínima de atratividade")
        else: chk("s","✅ ROE adequado",f"{roe:.1f}%")
    except: pass

    # Tendência receita
    if "receita bruta de vendas" in df_a.columns and len(df_a)>=3:
        u3=pd.to_numeric(df_a["receita bruta de vendas"],errors="coerce").tail(3)
        if len(u3)==3:
            if u3.iloc[-1]<u3.iloc[-2]<u3.iloc[-3]:
                chk("d","📉 Receita em QUEDA","3 períodos consecutivos de queda — atenção urgente")
            elif u3.iloc[-1]>u3.iloc[-2]>u3.iloc[-3]:
                chk("s","📈 Receita em CRESCIMENTO","3 períodos consecutivos de crescimento")

    pd_=sum(1 for a in alertas if a[0]=="d")
    pw_=sum(1 for a in alertas if a[0]=="w")
    ps_=sum(1 for a in alertas if a[0]=="s")
    mc(c2,"🔴 Críticos",str(pd_),"r")
    mc(c3,"⚠️ Atenção",str(pw_),"y")
    mc(c4,"✅ Saudável",str(ps_),"g")

    # Diagnóstico
    sec("📋 Diagnóstico Detalhado")
    for tipo,msg,detalhe in sorted(alertas,key=lambda x:{"d":0,"w":1,"s":2}[x[0]]):
        st.markdown(f'<div class="al-{tipo}"><b>{msg}</b>'
                    f'{"<br><span style=\'font-size:.8rem;opacity:.85\'>"+detalhe+"</span>" if detalhe else ""}'
                    f'</div>',unsafe_allow_html=True)

    # Anomalias com gráfico
    sec("🔍 Detecção de Anomalias")
    st.markdown('<div class="al-i">Pontos fora do padrão histórico — variação acima de 1,3x o desvio padrão móvel.</div>',unsafe_allow_html=True)
    campos_anom=[
        ("receita bruta de vendas","#2563EB","Receita Bruta"),
        ("CMV (custo da mercadoria vendida)","#DC2626","CMV"),
        ("despesas administrativas","#D97706","Desp. Administrativas"),
        ("lucro líquido","#059669","Lucro Líquido"),
        ("EBITDA","#7C3AED","EBITDA")]
    achou_anom=False
    for campo_a2,cor_a,nm_a in campos_anom:
        if campo_a2 not in df_a.columns: continue
        anom=detectar_anomalias(df_a[campo_a2]); n_anom=int(anom.sum())
        if n_anom>0:
            achou_anom=True
            ma=df_a[cm][anom].tolist() if cm else list(df_a.index[anom])
            st.markdown(f'<div class="al-w">⚠️ <b>{nm_a}</b>: {n_anom} ponto(s) atípico(s) — '
                       f'períodos: {", ".join(str(m) for m in ma[:6])}</div>',unsafe_allow_html=True)
    if not achou_anom:
        st.markdown('<div class="al-s">✅ Nenhuma anomalia detectada nos campos analisados.</div>',unsafe_allow_html=True)

    # Tabela resumo por período
    sec("📊 Resumo de Saúde por Período")
    st.markdown('<div class="al-i">✅ = indicador positivo/saudável | ⚠️ = atenção | 🔴 = crítico</div>',unsafe_allow_html=True)
    if ca and cm:
        res=[]
        for _,row in df_a.iterrows():
            def status(campo,inv=False,limites=None):
                try:
                    v=float(row.get(campo,0) or 0)
                    if limites:
                        if v>=limites[1]: return "✅"
                        if v>=limites[0]: return "⚠️"
                        return "🔴"
                    if inv: return "⚠️" if v>60 else "✅"
                    return "✅" if v>0 else "🔴"
                except: return "—"
            sc_r=float(row.get("score_risco",0))
            sc_lbl="🟢" if sc_r>=80 else ("🟡" if sc_r>=60 else ("🟠" if sc_r>=40 else "🔴"))
            res.append({
                "Ano":row.get(ca,""),"Mês":row.get(cm,""),
                "Score":f"{sc_lbl} {sc_r:.0f}",
                "Receita":status("receita bruta de vendas"),
                "Lucro":status("lucro líquido"),
                "Mg Líquida":status("margem líquida %",limites=(0,5)),
                "Liquidez":status("liquidez corrente",limites=(1,1.5)),
                "Kanitz":status("kanitz",limites=(0,0)),
                "Ciclo Cx":status("ciclo de caixa",inv=True)})
        st.dataframe(pd.DataFrame(res),use_container_width=True,hide_index=True)

# ── ML ───────────────────────────────────────────────
elif pg=="ml":
    hdr("🔮 Projeções ML","Machine Learning — o sistema testa todos os modelos e escolhe o mais preciso")
    if not STATS_OK:
        st.markdown('<div class="al-d">❌ pip install statsmodels scikit-learn</div>',unsafe_allow_html=True)
    df=get_df()
    if df is None: no_data(); st.stop()
    cm=cm_(df); ca=ca_(df)

    # Explicação simples
    st.markdown("""<div class="al-i">
    🤖 <b>Como funciona:</b> O sistema testa automaticamente todos os modelos disponíveis
    (ARIMA, ExponentialSmoothing, SARIMAX, Holt, Prophet) para cada campo,
    compara o erro de cada um nos últimos 6 meses reais e escolhe o mais preciso.
    A banda cinza mostra o intervalo de incerteza ±15%.
    </div>""",unsafe_allow_html=True)

    # Filtro período + meses a projetar
    sec("⚙️ Configurações")
    col1,col2,col3=st.columns(3)
    anos_ml=["Todos"]+[str(a) for a in sorted(df[ca].dropna().unique().tolist())] if ca else ["Todos"]
    ano_ml=col1.selectbox("Ano base",anos_ml,key="ml_ano")
    df_ml=df[df[ca].astype(str)==ano_ml].reset_index(drop=True) if ano_ml!="Todos" else df.reset_index(drop=True)
    n_m=col2.slider("Meses a projetar",1,24,6)
    var_pct=col3.slider("Variação cenários (%)",5,30,15,step=5)

    if len(df_ml)<6:
        st.markdown('<div class="al-w">⚠️ Mínimo 6 períodos de dados para projetar.</div>',unsafe_allow_html=True)
        st.stop()

    mds_disp=[m for m,ok in MODELOS_ML.items() if ok]

    # Campos fixos principais
    campos_fixos=[
        # DRE
        ("receita bruta de vendas","💰 Receita Bruta","#2563EB"),
        ("receita líquida","📊 Receita Líquida","#2563EB"),
        ("lucro bruto","📈 Lucro Bruto","#059669"),
        ("lucro líquido","✅ Lucro Líquido","#059669"),
        ("EBITDA","⚡ EBITDA","#D97706"),
        ("margem bruta %","📊 Margem Bruta %","#7C3AED"),
        ("margem contrib %","📊 Margem Contribuição %","#7C3AED"),
        ("margem líquida %","📉 Margem Líquida %","#DC2626"),
        ("EBITDA %","⚡ EBITDA %","#D97706"),
        ("despesas comerciais","🛒 Desp. Comerciais","#DC2626"),
        ("despesas administrativas","🏢 Desp. Administrativas","#DC2626"),
        # Balanço
        ("disponibilidades saldo","🏦 Disponibilidades","#0891B2"),
        ("contas a receber saldo","📥 Contas a Receber","#0891B2"),
        ("estoque final do mês de mercadorias para revenda saldo","📦 Estoques","#D97706"),
        ("ativo total","🏛️ Ativo Total","#2563EB"),
        ("pass total","⚠️ Passivo Total","#DC2626"),
        ("PL","💎 Patrimônio Líquido","#059669"),
        # Indicadores
        ("liquidez corrente","💧 Liquidez Corrente","#0891B2"),
        ("liquidez imediata","💧 Liquidez Imediata","#0891B2"),
        ("kanitz","🌡️ Kanitz","#7C3AED"),
        ("ROE","💹 ROE %","#059669"),
        ("PMR","📅 PMR (dias)","#D97706"),
        ("PMP","📅 PMP (dias)","#059669"),
        ("ciclo de caixa","🔄 Ciclo de Caixa","#DC2626"),
        # Fluxo
        ("Disponibilidades entradas","💵 Entradas Caixa","#059669"),
        ("Disponibilidades Saida","💸 Saídas Caixa","#DC2626"),
    ]
    campos_proj=[(c,l,cor_c) for c,l,cor_c in campos_fixos if c in df_ml.columns]

    if st.button("🚀 Gerar Projeções",use_container_width=True):
        projs={}; pb=st.progress(0)
        with st.spinner("🤖 Testando modelos e gerando projeções..."):
            for i,(campo,lbl,cor_c) in enumerate(campos_proj):
                try:
                    melhor,rank=melhor_modelo(df_ml[campo],mds_disp)
                    proj=treinar(df_ml[campo],melhor,n_m)
                    if proj is not None:
                        projs[campo]={"modelo":melhor,"valores":proj.tolist(),"rank":rank,"lbl":lbl,"cor":cor_c}
                except: pass
                pb.progress((i+1)/len(campos_proj))
        pb.empty()
        st.session_state.projecoes=projs
        st.markdown(f'<div class="al-s">✅ {len(projs)} campos projetados para {n_m} meses.</div>',unsafe_allow_html=True)
        addlog(f"ML: {len(projs)} campos × {n_m} meses")

    if st.session_state.projecoes:
        projs=st.session_state.projecoes

        TH_ML=dict(plot_bgcolor="white",paper_bgcolor="white",
            font=dict(color="#6B7280",size=10,family="Inter"),
            xaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=False,tickangle=-35),
            yaxis=dict(gridcolor="#F3F4F6",linecolor="#E8ECF0",showgrid=True),
            margin=dict(l=8,r=8,t=44,b=40),
            legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.3,font=dict(size=9)),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="white",bordercolor="#E8ECF0",font=dict(color="#111827",size=11)))

        x_h=df_ml[cm].astype(str) if cm else pd.Series(range(len(df_ml))).astype(str)
        if ca and cm:
            x_h=df_ml[cm].astype(str)+"/"+df_ml[ca].astype(str).str[-2:]
        x_p=[f"M+{i+1}" for i in range(n_m)]

        # Gráficos 2 por linha
        campos_list=list(projs.items())
        for idx in range(0,len(campos_list),2):
            cols=st.columns(2)
            for j,col in enumerate(cols):
                if idx+j>=len(campos_list): break
                campo,(p)=campos_list[idx+j]
                lbl=p.get("lbl",campo)
                cor_c=p.get("cor","#2563EB")
                v_hist=pd.to_numeric(df_ml[campo],errors="coerce")
                v_proj=p["valores"]
                # Sempre pega o último mês real do dataset completo — não do filtrado
                v_at=float(pd.to_numeric(df[campo],errors="coerce").dropna().iloc[-1]) if campo in df.columns else 0
                v_pr=v_proj[-1] if v_proj else 0
                var=safe(v_pr-v_at,abs(v_at))*100

                # Ranking modelos
                rank_s=sorted(p.get("rank",{}).items(),key=lambda x:x[1])
                melhor_nm=p["modelo"]

                fig=go.Figure()
                # Histórico
                fig.add_trace(go.Scatter(x=x_h,y=v_hist,name="Histórico",
                  mode="lines+markers",line=dict(color=cor_c,width=2.2),
                  marker=dict(size=4,color=cor_c,line=dict(color="white",width=1.5)),
                  hovertemplate=f"<b>Histórico</b><br>%{{x}}<br>%{{y:,.1f}}<extra></extra>"))
                # Projeção base
                fig.add_trace(go.Scatter(x=x_p,y=v_proj,name=f"Projeção ({melhor_nm})",
                  mode="lines+markers",line=dict(color=cor_c,width=2,dash="dash"),
                  marker=dict(size=6,color=cor_c,symbol="diamond",line=dict(color="white",width=1.5)),
                  hovertemplate=f"<b>Projeção</b><br>%{{x}}<br>%{{y:,.1f}}<extra></extra>"))
                # Banda incerteza
                y_up=[v*(1+var_pct/100) for v in v_proj]
                y_dn=[v*(1-var_pct/100) for v in v_proj]
                fig.add_trace(go.Scatter(x=x_p+x_p[::-1],y=y_up+y_dn[::-1],
                  fill="toself",fillcolor="rgba(107,114,128,.08)",
                  line=dict(color="rgba(0,0,0,0)"),name=f"±{var_pct}%",showlegend=True))

                fig.update_layout(
                  title=dict(text=f"{lbl} — {var:+.1f}% em {n_m} meses ({melhor_nm})",
                    font=dict(size=11,color="#111827")),**TH_ML)
                col.plotly_chart(fig,use_container_width=True)

        # Cenários e ranking
        sec("🎯 Cenários e Ranking de Modelos")
        for campo,(p) in projs.items():
            lbl=p.get("lbl",campo)
            v_hist=pd.to_numeric(df_ml[campo],errors="coerce").dropna()
            v_at=float(df[campo].dropna().iloc[-1]) if campo in df.columns and len(df[campo].dropna())>0 else 0
            v_pr=p["valores"][-1] if p["valores"] else 0
            var=safe(v_pr-v_at,abs(v_at))*100
            rank_s=sorted(p.get("rank",{}).items(),key=lambda x:x[1])

            def fmt_titulo(campo,v):
                pct_c=["margem bruta %","margem contrib %","margem líquida %",
                        "EBITDA %","liquidez corrente","liquidez imediata","ROE"]
                dias_c=["PMR","PMP","ciclo de caixa"]
                if campo in pct_c: return fmt(v,"pct")
                if campo in dias_c: return fmt(v,"d")
                if campo=="kanitz": return f"{v:.2f}"
                return fmt(v)
            with st.expander(f"{lbl} — Melhor modelo: {p['modelo']} | Projeção: {fmt_titulo(campo,v_pr)} ({var:+.1f}%)"):
                # Cenários
                c1,c2,c3=st.columns(3)
                def fmt_c(v):
                    pct_c=["margem bruta %","margem contrib %","margem líquida %",
                            "EBITDA %","liquidez corrente","liquidez imediata","ROE"]
                    dias_c=["PMR","PMP","ciclo de caixa"]
                    if campo in pct_c: return fmt(v,"pct")
                    if campo in dias_c: return fmt(v,"d")
                    if campo=="kanitz": return f"{v:.2f}"
                    return fmt(v)

                mc(c1,f"🐻 Pessimista (-{var_pct}%)",fmt_c(v_pr*(1-var_pct/100)),"r",f"vs atual: {fmt_c(v_at)}")
                mc(c2,"📊 Base (projeção)",fmt_c(v_pr),"y",f"{var:+.1f}% vs atual")
                mc(c3,f"🐂 Otimista (+{var_pct}%)",fmt_c(v_pr*(1+var_pct/100)),"g",f"vs atual: {fmt_c(v_at)}")
                # Ranking modelos
                v_hist=pd.to_numeric(df_ml[campo],errors="coerce").dropna()
                media_serie=float(v_hist.mean()) if len(v_hist)>0 else 1
                # Formata média histórica corretamente por tipo de campo
                pct_campos=["margem bruta %","margem contrib %","margem líquida %",
                            "EBITDA %","liquidez corrente","liquidez imediata","ROE"]
                dias_campos=["PMR","PMP","ciclo de caixa"]
                if campo in pct_campos:
                    media_fmt=fmt(media_serie,"pct")
                    unidade="pontos percentuais"
                elif campo in dias_campos:
                    media_fmt=fmt(media_serie,"d")
                    unidade="dias"
                elif campo=="kanitz":
                    media_fmt=f"{media_serie:.2f}"
                    unidade="pontos no termômetro de Kanitz"
                else:
                    media_fmt=fmt(media_serie)
                    unidade="reais"

                st.markdown(f"""**Como chegamos a essa projeção:**

O sistema usou os últimos **{len(v_hist)}** períodos históricos para treinar cada modelo.
Depois testou a precisão de cada um nos últimos **6 meses reais** — comparando o que o modelo teria previsto com o que realmente aconteceu.
O vencedor foi **{p['modelo']}** com menor erro relativo.
O erro % abaixo mostra o desvio médio da previsão em relação à média histórica de **{media_fmt}** ({unidade}).
Quanto menor o %, mais preciso o modelo foi nos dados reais.

**Ranking de modelos — erro relativo (% sobre a média histórica):**""")
                cols_r=st.columns(max(min(len(rank_s),5),1))
                for i,(mod,mse) in enumerate(rank_s[:5]):
                    ico=["🥇","🥈","🥉","4️⃣","5️⃣"][i]
                    desc={"ARIMA":"Captura tendências e autocorrelações",
                          "ExponentialSmoothing":"Pesa mais os dados recentes",
                          "SARIMAX":"Captura sazonalidade anual",
                          "Holt":"Tendência com amortecimento",
                          "Prophet":"IA do Meta para séries temporais"}.get(mod,"")
                    # Converte MSE para RMSE% (erro relativo à média da série)
                    media_serie=float(v_hist.mean()) if len(v_hist)>0 else 1
                    rmse=float(mse**0.5) if mse<float("inf") else 0
                    erro_pct=safe(rmse,abs(media_serie))*100
                    cls_err="g" if erro_pct<5 else ("y" if erro_pct<15 else "r")
                    cols_r[i].markdown(f'<div class="mc"><div class="mc-lbl">{ico} {mod}</div>'
                      f'<div class="mc-val {cls_err}" style="font-size:1rem">{erro_pct:.1f}% erro</div>'
                      f'<div class="mc-sub">{desc}</div></div>',unsafe_allow_html=True)

        # Tabela resumo
        sec("📋 Resumo de Todas as Projeções")
        def fmt_campo(campo_f, v):
            pct_campos=["margem bruta %","margem contrib %","margem líquida %",
                        "EBITDA %","liquidez corrente","liquidez imediata","ROE"]
            dias_campos=["PMR","PMP","ciclo de caixa"]
            if campo_f in pct_campos: return fmt(v,"pct")
            if campo_f in dias_campos: return fmt(v,"d")
            if campo_f=="kanitz": return f"{v:.2f}"
            return fmt(v)
        res=[]
        for campo_r,p in projs.items():
            lbl=p.get("lbl",campo_r)
            v_a=float(df[campo_r].dropna().iloc[-1]) if campo_r in df.columns and len(df[campo_r].dropna())>0 else 0
            v_p2=p["valores"][-1] if p["valores"] else 0
            var2=safe(v_p2-v_a,abs(v_a))*100
            res.append({
                "Campo":lbl,"Modelo":p["modelo"],
                "Atual":fmt_campo(campo_r,v_a),
                "Projeção":fmt_campo(campo_r,v_p2),
                f"Pessimista (-{var_pct}%)":fmt_campo(campo_r,v_p2*(1-var_pct/100)),
                f"Otimista (+{var_pct}%)":fmt_campo(campo_r,v_p2*(1+var_pct/100)),
                "Var%":f"{var2:+.1f}%"})
        if res: st.dataframe(pd.DataFrame(res),use_container_width=True,hide_index=True)

# ── CENÁRIOS FP&A ───────────────────────────────────
elif pg=="cenarios":
    hdr("📊 Cenários FP&A","DRE, Balanço e Fluxo de Caixa projetados com ML")
    df=get_df()
    if df is None: no_data(); st.stop()
    if not st.session_state.projecoes:
        st.markdown('<div class="al-w">⚠️ Gere as projeções primeiro em <b>🔮 Projeções ML</b>.</div>',unsafe_allow_html=True)
        st.stop()

    projs=st.session_state.projecoes
    n_m=len(list(projs.values())[0]["valores"]) if projs else 6
    cm=cm_(df); ca=ca_(df)

    sec("⚙️ Configurações")
    c1,c2=st.columns(2)
    cenario=c1.radio("Cenário",["📊 Base","🐻 Pessimista","🐂 Otimista"],horizontal=True)
    demo=c2.radio("Demonstração",["📋 DRE","🏦 Balanço","💰 Fluxo de Caixa"],horizontal=True)
    var_pct=st.session_state.get("var_pct_ml",15)

    # Fator do cenário
    fator=1.0
    if "Pessimista" in cenario: fator=1-var_pct/100
    elif "Otimista" in cenario: fator=1+var_pct/100

    # Último valor real de cada campo
    ul_real=df.iloc[-1]

    # Session state para edições
    if "fp_edicoes" not in st.session_state: st.session_state.fp_edicoes={}
    chave_cen=f"{cenario}_{demo}"
    if chave_cen not in st.session_state.fp_edicoes:
        st.session_state.fp_edicoes[chave_cen]={}

    def get_proj(campo):
        base=[]
        if campo in projs:
            base=[v*fator for v in projs[campo]["valores"]]
        else:
            v=float(ul_real.get(campo,0) or 0)
            base=[v]*n_m
        edicoes=st.session_state.fp_edicoes[chave_cen].get(campo,{})
        for i,v_edit in edicoes.items():
            if 0<=int(i)<len(base): base[int(i)]=v_edit
        return base

    def painel_edicao(campos_editaveis):
        st.divider()
        with st.expander("✏️ Ajustar Premissas — edite valores e recalcule"):
            tem_edicao=any(st.session_state.fp_edicoes[chave_cen].get(c) for c,_ in campos_editaveis)
            if tem_edicao:
                c_rst=st.columns([3,1])
                c_rst[0].markdown('<div class="al-w">✏️ Há valores editados — demonstração recalculada.</div>',unsafe_allow_html=True)
                if c_rst[1].button("🔄 Resetar tudo",key=f"rst_all_{chave_cen}",use_container_width=True):
                    st.session_state.fp_edicoes[chave_cen]={}; st.rerun()
            for campo,lbl in campos_editaveis:
                if campo in projs:
                    base_orig=[v*fator for v in projs[campo]["valores"]]
                else:
                    v0=float(ul_real.get(campo,0) or 0)
                    base_orig=[v0]*n_m
                edicoes=st.session_state.fp_edicoes[chave_cen].get(campo,{})
                st.markdown(f"**{lbl}** — Base ML: {fmt(base_orig[-1])}")
                modo=st.radio("Modo",["% variação","R$ valor"],horizontal=True,
                  key=f"modo_{campo}_{chave_cen}",label_visibility="collapsed")
                aplicar=st.radio("Aplicar a",["Todos os meses","Mês a mês"],horizontal=True,
                  key=f"aplic_{campo}_{chave_cen}",label_visibility="collapsed")
                novos={}; mudou=False
                if aplicar=="Todos os meses":
                    if modo=="% variação":
                        pct_g=st.slider(f"Variação %",min_value=-50,max_value=100,value=0,step=1,
                          key=f"pct_g_{campo}_{chave_cen}")
                        if pct_g!=0:
                            for i in range(n_m):
                                novos[str(i)]=round(base_orig[i]*(1+pct_g/100),2)
                            mudou=novos!=edicoes
                        elif edicoes:
                            mudou=True
                    else:
                        v_ref=round(float(base_orig[0]),0)
                        v_g=st.number_input(f"Novo valor R$ (todos os meses)",
                          value=v_ref,step=max(abs(v_ref)*0.05,1000.),format="%.0f",
                          key=f"val_g_{campo}_{chave_cen}")
                        if v_g!=v_ref:
                            for i in range(n_m): novos[str(i)]=float(v_g)
                            mudou=novos!=edicoes
                        elif edicoes: mudou=True
                else:
                    n_cols=min(n_m,6)
                    for bloco in range(0,n_m,n_cols):
                        cols_m=st.columns(n_cols)
                        for j in range(n_cols):
                            i=bloco+j
                            if i>=n_m: break
                            m=meses_proj[i]
                            v_base=round(float(base_orig[i]),0)
                            v_edit=float(edicoes.get(str(i),v_base))
                            if modo=="% variação":
                                pct_atual=round((v_edit/v_base-1)*100 if v_base!=0 else 0,1)
                                pct_m=cols_m[j].number_input(m,value=pct_atual,
                                  step=1.,format="%.1f",
                                  key=f"pct_m_{campo}_{i}_{chave_cen}")
                                novo_v=round(v_base*(1+pct_m/100),2)
                                if abs(novo_v-v_base)>0.01: novos[str(i)]=novo_v
                            else:
                                novo_v=cols_m[j].number_input(m,value=v_edit,
                                  step=max(abs(v_base)*0.05,1000.),format="%.0f",
                                  key=f"val_m_{campo}_{i}_{chave_cen}")
                                if abs(novo_v-v_base)>0.01: novos[str(i)]=round(float(novo_v),2)
                    mudou=novos!=edicoes
                if mudou:
                    if novos: st.session_state.fp_edicoes[chave_cen][campo]=novos
                    else: st.session_state.fp_edicoes[chave_cen].pop(campo,None)
                    st.rerun()
                if edicoes:
                    if st.button(f"↩️ Resetar {lbl}",key=f"rst_{campo}_{chave_cen}"):
                        st.session_state.fp_edicoes[chave_cen].pop(campo,None); st.rerun()
                st.divider()

    # Colunas dos meses — calcula meses reais após o último período
    MESES_NOMES=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    ul_real=df.iloc[-1]
    try:
        ult_mes=str(ul_real.get(cm,"jan")).lower()[:3]
        ult_ano=int(ul_real.get(ca,2024))
        idx_mes=MESES_NOMES.index(ult_mes) if ult_mes in MESES_NOMES else 11
        meses_proj=[]
        for i in range(n_m):
            idx=(idx_mes+1+i)%12
            ano=ult_ano+((idx_mes+1+i)//12)
            meses_proj.append(f"{MESES_NOMES[idx]}/{ano}")
    except:
        meses_proj=[f"M+{i+1}" for i in range(n_m)]

    col_info,col_rst=st.columns([4,1])
    col_info.markdown(f'<div class="al-i">📌 Cenário: <b>{cenario}</b> | {n_m} meses projetados | Fator: {"×"+str(round(fator,2)) if fator!=1 else "Base"}</div>',unsafe_allow_html=True)
    if col_rst.button("🔄 Resetar tudo",key="rst_all",use_container_width=True):
        st.session_state.fp_edicoes[chave_cen]={}
        st.rerun()
    # Aviso se há edições ativas
    if st.session_state.fp_edicoes.get(chave_cen):
        campos_edit=list(st.session_state.fp_edicoes[chave_cen].keys())
        st.markdown(f'<div class="al-w">✏️ Valores editados manualmente em: <b>{", ".join(campos_edit)}</b> — clique em Resetar para voltar ao ML.</div>',unsafe_allow_html=True)

    # ── DRE PROJETADA
    if "DRE" in demo:
        sec("📋 DRE Projetada")

        rb  = get_proj("receita bruta de vendas")
        imp = get_proj("impostos sobre vendas")
        dev = get_proj("devoluções de vendas")
        imp = get_proj("impostos sobre vendas")
        dev = get_proj("devoluções de vendas")
        rl  = [rb[i]-imp[i]-dev[i] for i in range(n_m)]
        cmv = get_proj("CMV (custo da mercadoria vendida)")
        lb  = [rl[i]-cmv[i] for i in range(n_m)]
        dc  = get_proj("despesas comerciais")
        mc_ = [lb[i]-dc[i] for i in range(n_m)]
        da  = get_proj("despesas administrativas")
        df_ = get_proj("despesas financeiras líquidas")
        dep = get_proj("despesas com depreciações e amortizações")
        lo  = [lb[i]-dc[i]-da[i]-df_[i]-dep[i] for i in range(n_m)]
        rno = get_proj("receitas não operacionais")
        dno = get_proj("despesas não operacionais")
        ir  = get_proj("provisão para imposto de renda")
        cs  = get_proj("provisão para contribuição social")
        ll  = [lo[i]+rno[i]-dno[i]-ir[i]-cs[i] for i in range(n_m)]
        ebt = [ll[i]+ir[i]+cs[i]+df_[i]+dep[i] for i in range(n_m)]

        # Margens
        def pct(num,den,i): return safe(num[i],den[i])*100 if den[i]!=0 else 0
        def ah(serie,i): return safe(serie[i]-serie[i-1],abs(serie[i-1]))*100 if i>0 else 0

        linhas_dre=[
            ("cat","(+) RECEITA BRUTA",rb,False),
            ("sub","  (-) Impostos",imp,True),
            ("sub","  (-) Devoluções",dev,True),
            ("tot","= RECEITA LÍQUIDA",rl,False),
            ("sub","  (-) CMV",cmv,True),
            ("tot","= LUCRO BRUTO",lb,False),
            ("pct_rb","  Margem Bruta %",lb,False),
            ("sub","  (-) Desp. Comerciais",dc,True),
            ("tot","= MARGEM CONTRIB.",mc_,False),
            ("pct_rb","  Margem Contrib. %",mc_,False),
            ("sub","  (-) Desp. Adm.",da,True),
            ("sub","  (-) Desp. Fin.",df_,True),
            ("sub","  (-) Depreciação",dep,True),
            ("tot","= LUCRO OPERACIONAL",lo,False),
            ("pct_rb","  Margem Op. %",lo,False),
            ("sub","  (+/-) Não Operac.",rno,False),
            ("sub","  (-) IR/CSLL",[ir[i]+cs[i] for i in range(n_m)],True),
            ("tot","= LUCRO LÍQUIDO",ll,False),
            ("pct_rb","  Margem Líquida %",ll,False),
            ("tot","  EBITDA",ebt,False),
            ("pct_rb","  EBITDA %",ebt,False),
        ]

        header_d="<tr><th>Descrição</th>"+"".join(f"<th>{m}</th><th>AV%</th><th>AH%</th>" for m in meses_proj)+"</tr>"
        rows_d=""
        for tipo,desc,serie,inv in linhas_dre:
            cls_tr={"cat":"cat","tot":"tot","pct_rb":"pct","sub":"sub"}.get(tipo,"")
            row=f'<tr class="{cls_tr}"><td>{desc}</td>'
            for i in range(n_m):
                if tipo=="pct_rb":
                    v=pct(serie,rb,i)
                    dlt=v-pct(serie,rb,i-1) if i>0 else 0
                    row+=f'<td class="pct">{fmt(v,"pct")}</td>'
                    row+=f'<td class="{"pos" if dlt>0 else "neg" if dlt<0 else "neu"}">{dlt:+.1f}pp</td>'
                    row+=f'<td></td>'
                else:
                    v=float(serie[i])
                    a_v=safe(v,rb[i])*100
                    a_h=ah(serie,i)
                    cls_v="neg" if (inv and v!=0) else cor(v)
                    row+=f'<td class="{cls_v}">{fmt(v)}</td>'
                    row+=f'<td class="{cls_pct(a_v,inv)}">{fmt(a_v,"pct")}</td>'
                    row+=f'<td class="{cls_pct(a_h,inv)}">{fmt(a_h,"pct")}</td>'
            rows_d+=row+"</tr>"
        st.markdown(f'<div class="dre-wrap" style="overflow-x:auto"><table class="dre" style="min-width:900px">{header_d}{rows_d}</table></div>',unsafe_allow_html=True)

        painel_edicao([
            ("receita bruta de vendas","💰 Receita Bruta"),
            ("impostos sobre vendas","🏛️ Impostos s/ Vendas"),
            ("devoluções de vendas","↩️ Devoluções"),
            ("CMV (custo da mercadoria vendida)","📦 CMV"),
            ("despesas comerciais","🛒 Desp. Comerciais"),
            ("despesas administrativas","🏢 Desp. Administrativas"),
            ("despesas financeiras líquidas","💳 Desp. Financeiras"),
            ("despesas com depreciações e amortizações","📉 Depreciação"),
        ])

    # ── BALANÇO PROJETADO
    elif "Balanço" in demo:
        sec("🏦 Balanço Projetado")
        disp = get_proj("disponibilidades saldo")
        cr   = get_proj("contas a receber saldo")
        est  = get_proj("estoque final do mês de mercadorias para revenda saldo")
        oac  = get_proj("Outros AC")
        anc  = get_proj("Ativo NC")
        ac   = [disp[i]+cr[i]+est[i]+oac[i] for i in range(n_m)]
        at   = [ac[i]+anc[i] for i in range(n_m)]
        forn = get_proj("contas a pagar de fornecedores saldo")
        pf   = get_proj("Passivos Financeiros")
        opc  = get_proj("Outros PC")
        pnc  = get_proj("Passivo NC")
        pc   = [forn[i]+pf[i]+opc[i] for i in range(n_m)]
        pt   = [pc[i]+pnc[i] for i in range(n_m)]
        pl   = [at[i]-pt[i] for i in range(n_m)]

        def ah(serie,i): return safe(serie[i]-serie[i-1],abs(serie[i-1]))*100 if i>0 else 0

        linhas_bal=[
            ("cat","ATIVO",None),
            ("sub","  Disponibilidades",disp,False),
            ("sub","  Contas a Receber",cr,False),
            ("sub","  Estoques",est,False),
            ("sub","  Outros AC",oac,False),
            ("tot","= ATIVO CIRCULANTE",ac,False),
            ("sub","  Ativo NC",anc,False),
            ("tot","= ATIVO TOTAL",at,False),
            ("cat","PASSIVO",None),
            ("sub","  Fornecedores",forn,True),
            ("sub","  Pass. Financeiros",pf,True),
            ("sub","  Outros PC",opc,True),
            ("tot","= PASSIVO CIRCULANTE",pc,True),
            ("sub","  Passivo NC",pnc,True),
            ("tot","= PASSIVO TOTAL",pt,True),
            ("tot","= PATRIMÔNIO LÍQUIDO",pl,False),
        ]

        header_b="<tr><th>Descrição</th>"+"".join(f"<th>{m}</th><th>AV%</th><th>AH%</th>" for m in meses_proj)+"</tr>"
        rows_b=""
        for item in linhas_bal:
            if item[2] is None:
                rows_b+=f'<tr class="cat"><td>{item[1]}</td>'+"".join("<td></td><td></td><td></td>" for _ in meses_proj)+"</tr>"
                continue
            tipo,desc,serie,inv=item
            cls_tr={"tot":"tot","sub":"sub"}.get(tipo,"")
            row=f'<tr class="{cls_tr}"><td>{desc}</td>'
            for i in range(n_m):
                v=float(serie[i])
                at_i=float(at[i]) if at[i] else 1
                a_v=safe(v,at_i)*100
                a_h=ah(serie,i)
                cls_v="neg" if (inv and v!=0) else cor(v)
                row+=f'<td class="{cls_v}">{fmt(v)}</td>'
                row+=f'<td class="{cls_pct(a_v,inv)}">{fmt(a_v,"pct")}</td>'
                row+=f'<td class="{cls_pct(a_h,inv)}">{fmt(a_h,"pct")}</td>'
            rows_b+=row+"</tr>"
        st.markdown(f'<div class="dre-wrap" style="overflow-x:auto"><table class="dre" style="min-width:900px">{header_b}{rows_b}</table></div>',unsafe_allow_html=True)

        painel_edicao([
            ("disponibilidades saldo","🏦 Disponibilidades"),
            ("contas a receber saldo","📥 Contas a Receber"),
            ("estoque final do mês de mercadorias para revenda saldo","📦 Estoques"),
            ("Outros AC","📋 Outros AC"),
            ("Ativo NC","🏛️ Ativo NC"),
            ("contas a pagar de fornecedores saldo","🏭 Fornecedores"),
            ("Passivos Financeiros","💳 Pass. Financeiros"),
            ("Outros PC","📋 Outros PC"),
            ("Passivo NC","🏛️ Passivo NC"),
        ])

    # ── FLUXO PROJETADO
    elif "Fluxo" in demo:
        sec("💰 Fluxo de Caixa Projetado")
        ent  = get_proj("Disponibilidades entradas")
        sai  = get_proj("Disponibilidades Saida")
        ev=float(st.session_state.get("entradas_vista",0))
        freq=st.session_state.get("freq_fluxo","Mensal")
        ev_m=ev*22 if freq=="Diário" else ev
        ent=[ent[i]+ev_m for i in range(n_m)]
        sp   = [ent[i]-sai[i] for i in range(n_m)]
        si   = float(st.session_state.get("saldo_ini",0))
        sa   = []
        for i in range(n_m):
            sa.append((sa[i-1] if i>0 else si)+sp[i])

        def ah(serie,i): return safe(serie[i]-serie[i-1],abs(serie[i-1]))*100 if i>0 else 0

        linhas_fc=[
            ("tot","Total Entradas",ent,False),
            ("sub","  (-) Total Saídas",sai,True),
            ("tot","= Saldo do Período",sp,False),
            ("tot","= Saldo Acumulado",sa,False),
        ]

        header_f="<tr><th>Descrição</th>"+"".join(f"<th>{m}</th><th>AH%</th>" for m in meses_proj)+"</tr>"
        rows_f=""
        for tipo,desc,serie,inv in linhas_fc:
            cls_tr={"tot":"tot","sub":"sub"}.get(tipo,"")
            row=f'<tr class="{cls_tr}"><td>{desc}</td>'
            for i in range(n_m):
                v=float(serie[i])
                a_h=ah(serie,i)
                cls_v="neg" if (inv and v!=0) else cor(v)
                row+=f'<td class="{cls_v}">{fmt(v)}</td>'
                row+=f'<td class="{cls_pct(a_h,inv)}">{fmt(a_h,"pct")}</td>'
            rows_f+=row+"</tr>"
        st.markdown(f'<div class="dre-wrap" style="overflow-x:auto"><table class="dre" style="min-width:700px">{header_f}{rows_f}</table></div>',unsafe_allow_html=True)

        # KPIs fluxo
        st.divider()
        k=st.columns(4)
        mc(k[0],"Saldo Inicial",fmt(si),"b")
        mc(k[1],"Total Entradas",fmt(sum(ent)),"g",f"Média: {fmt(sum(ent)/n_m)}/mês")
        mc(k[2],"Total Saídas",fmt(sum(sai)),"r",f"Média: {fmt(sum(sai)/n_m)}/mês")
        sf=sa[-1]; mc(k[3],"Saldo Final Projetado",fmt(sf),cor(sf))

        painel_edicao([
            ("Disponibilidades entradas","💵 Entradas"),
            ("Disponibilidades Saida","💸 Saídas"),
        ])

# ── EXPORTAR ────────────────────────────────────────
elif pg=="exportar":
    hdr("💾 Exportar","CSV, Excel multi-abas e JSON para Power BI")
    df=get_df()
    if df is None: no_data(); st.stop()
    p2=load_cli(st.session_state.cid) if st.session_state.cid else {}
    nid=gid(p2.get("nome","dados") if p2 else "dados")
    df_exp=df.copy()
    if "Data" in df_exp.columns:
        df_exp["Data"]=pd.to_datetime(df_exp["Data"],errors="coerce").dt.strftime("%d/%m/%Y")
    if st.session_state.projecoes:
        st.markdown(f'<div class="al-i">📊 {len(st.session_state.projecoes)} campos de projeção incluídos</div>',unsafe_allow_html=True)
        for c2_,pe in st.session_state.projecoes.items():
            vals_e=pe["valores"]
            serie_e=pd.Series([np.nan]*(len(df_exp)-len(vals_e))+vals_e)
            df_exp[f"{c2_} (Proj.)"]=serie_e.values[:len(df_exp)]
    st.markdown(f'<div class="al-s">✅ <b>{len(df_exp)}</b> períodos · <b>{df_exp.shape[1]}</b> campos</div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        csv=df_exp.to_csv(sep=";",decimal=",",index=False,encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 CSV (Power BI)",csv,file_name=f"{nid}_analytics.csv",mime="text/csv",use_container_width=True)
    with c2:
        buf=BytesIO()
        with pd.ExcelWriter(buf,engine="openpyxl") as w:
            df_exp.to_excel(w,index=False,sheet_name="Dados")
            dre_c=[c for c in ["Ano","mês","receita bruta de vendas","receita líquida","lucro bruto","lucro líquido","EBITDA","margem líquida %","EBITDA %"] if c in df_exp.columns]
            if dre_c: df_exp[dre_c].to_excel(w,index=False,sheet_name="DRE")
            bal_c=[c for c in ["Ano","mês","ativo total","ativo circ","pass total","pass circ","PL","liquidez corrente"] if c in df_exp.columns]
            if bal_c: df_exp[bal_c].to_excel(w,index=False,sheet_name="Balanço")
        buf.seek(0)
        st.download_button("📥 Excel (3 abas)",buf.getvalue(),file_name=f"{nid}_analytics.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    with c3:
        st.download_button("📥 JSON",df_exp.to_json(orient="records",force_ascii=False,indent=2).encode(),
          file_name=f"{nid}_analytics.json",mime="application/json",use_container_width=True)
    sec("👁️ Preview")
    cm2=cm_(df_exp); ca2=ca_(df_exp)
    prev=[c for c in [ca2,cm2,"receita bruta de vendas","lucro bruto","lucro líquido","EBITDA %","kanitz","score_risco"] if c and c in df_exp.columns]
    st.dataframe(df_exp[prev] if prev else df_exp,use_container_width=True,height=380)
    if st.session_state.log:
        st.divider()
        with st.expander("📋 Log"):
            for l in st.session_state.log[:30]: st.caption(l)
