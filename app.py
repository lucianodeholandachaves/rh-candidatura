import streamlit as st
import json
import uuid
import datetime
import re
from pathlib import Path
import os
from supabase import create_client, Client

# ── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Candidatura – RH",
    page_icon="🎯",
    layout="centered",
)

# ── Estilos ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* fundo suave */
  [data-testid="stAppViewContainer"] {background: #f5f7fa;}
  /* card principal */
  .card {
    background: white;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.08);
    margin-bottom: 1.5rem;
  }
  /* badge de etapa */
  .step-badge {
    display: inline-block;
    background: #2563eb;
    color: white;
    border-radius: 999px;
    padding: 2px 14px;
    font-size: .8rem;
    font-weight: 600;
    margin-bottom: .5rem;
  }
  h2 {margin-top: 0;}
  .info-box {
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    padding: .8rem 1rem;
    font-size: .9rem;
    color: #1e3a5f;
    margin: .8rem 0;
  }
  /* botão principal */
  div.stButton > button[kind="primary"] {
    background: #2563eb;
    color: white;
    border-radius: 8px;
    padding: .6rem 2rem;
    font-weight: 600;
  }
  div.stButton > button[kind="primary"]:hover {background: #1d4ed8;}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

CARGOS = [
    # Administração & Gestão
    "Assistente Administrativo",
    "Auxiliar Administrativo",
    "Recepcionista",
    "Secretário(a) Executivo(a)",
    "Gerente Administrativo",
    "Diretor(a) Administrativo",
    "Analista Administrativo",
    # RH & Pessoas
    "Analista de RH",
    "Assistente de RH",
    "Recrutador(a)",
    "Especialista em Treinamento e Desenvolvimento",
    "Gerente de RH",
    "Diretor(a) de RH",
    "Analista de Departamento Pessoal",
    # Financeiro & Contabilidade
    "Analista Financeiro",
    "Assistente Financeiro",
    "Contador(a)",
    "Auxiliar de Contabilidade",
    "Analista de Controladoria",
    "Gerente Financeiro",
    "Diretor(a) Financeiro",
    "Tesoureiro(a)",
    "Analista de Custos",
    "Auditor(a) Interno",
    # TI & Tecnologia
    "Analista de TI",
    "Desenvolvedor(a) de Software",
    "Desenvolvedor(a) Front-end",
    "Desenvolvedor(a) Back-end",
    "Desenvolvedor(a) Full Stack",
    "Desenvolvedor(a) Mobile",
    "Engenheiro(a) de Software",
    "Analista de Sistemas",
    "Arquiteto(a) de Software",
    "DevOps Engineer",
    "Analista de Suporte Técnico",
    "Técnico(a) de TI",
    "Administrador(a) de Redes",
    "Analista de Segurança da Informação",
    "Analista de Dados",
    "Cientista de Dados",
    "Engenheiro(a) de Dados",
    "Analista de Business Intelligence",
    "UX/UI Designer",
    "Product Manager",
    "Scrum Master",
    # Comercial & Vendas
    "Representante de Vendas",
    "Consultor(a) de Vendas",
    "Gerente Comercial",
    "Diretor(a) Comercial",
    "Supervisor(a) de Vendas",
    "Executivo(a) de Contas",
    "Assistente Comercial",
    "Operador(a) de Televendas",
    "Promotor(a) de Vendas",
    # Marketing & Comunicação
    "Analista de Marketing",
    "Assistente de Marketing",
    "Gerente de Marketing",
    "Social Media",
    "Designer Gráfico",
    "Redator(a) / Copywriter",
    "Analista de SEO",
    "Gestor(a) de Tráfego Pago",
    "Produtor(a) de Conteúdo",
    "Fotógrafo(a)",
    "Videomaker",
    # Operações & Logística
    "Operador(a) de Logística",
    "Auxiliar de Logística",
    "Analista de Logística",
    "Gerente de Operações",
    "Supervisor(a) de Operações",
    "Almoxarife",
    "Auxiliar de Almoxarifado",
    "Motorista",
    "Entregador(a)",
    "Operador(a) de Empilhadeira",
    # Produção & Indústria
    "Auxiliar de Produção",
    "Operador(a) de Produção",
    "Supervisor(a) de Produção",
    "Gerente de Produção",
    "Técnico(a) de Manutenção",
    "Mecânico(a) Industrial",
    "Eletricista Industrial",
    "Técnico(a) de Qualidade",
    "Analista de Qualidade",
    "Engenheiro(a) de Produção",
    "Engenheiro(a) de Qualidade",
    # Atendimento & Customer Success
    "Atendente",
    "Operador(a) de Call Center",
    "Supervisor(a) de Atendimento",
    "Analista de Customer Success",
    "Gerente de Customer Success",
    # Jurídico
    "Advogado(a)",
    "Assistente Jurídico",
    "Analista Jurídico",
    "Paralegal",
    "Gerente Jurídico",
    # Saúde
    "Médico(a)",
    "Enfermeiro(a)",
    "Técnico(a) de Enfermagem",
    "Fisioterapeuta",
    "Nutricionista",
    "Psicólogo(a)",
    "Farmacêutico(a)",
    "Assistente Social",
    # Educação
    "Professor(a)",
    "Coordenador(a) Pedagógico",
    "Instrutor(a) de Treinamento",
    "Tutor(a) EAD",
    # Engenharia & Projetos
    "Engenheiro(a) Civil",
    "Engenheiro(a) Elétrico",
    "Engenheiro(a) Mecânico",
    "Engenheiro(a) Químico",
    "Analista de Projetos",
    "Gerente de Projetos",
    "Arquiteto(a)",
    "Técnico(a) em Edificações",
    # Compras & Supply Chain
    "Analista de Compras",
    "Assistente de Compras",
    "Gerente de Compras",
    "Analista de Supply Chain",
    # Outros
    "Estagiário(a)",
    "Jovem Aprendiz",
    "Outro (digitar abaixo)",
]

def validar_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

PAISES = {
    "🇧🇷 +55 Brasil": "+55",
    "🇺🇸 +1 EUA / Canadá": "+1",
    "🇵🇹 +351 Portugal": "+351",
    "🇦🇷 +54 Argentina": "+54",
    "🇨🇱 +56 Chile": "+56",
    "🇨🇴 +57 Colômbia": "+57",
    "🇲🇽 +52 México": "+52",
    "🇵🇾 +595 Paraguai": "+595",
    "🇺🇾 +598 Uruguai": "+598",
    "🇧🇴 +591 Bolívia": "+591",
    "🇵🇪 +51 Peru": "+51",
    "🇻🇪 +58 Venezuela": "+58",
    "🇪🇸 +34 Espanha": "+34",
    "🇩🇪 +49 Alemanha": "+49",
    "🇬🇧 +44 Reino Unido": "+44",
    "🇮🇹 +39 Itália": "+39",
    "🇫🇷 +33 França": "+33",
    "🇯🇵 +81 Japão": "+81",
    "🇨🇳 +86 China": "+86",
    "🇦🇴 +244 Angola": "+244",
    "🇲🇿 +258 Moçambique": "+258",
    "Outro país": "",
}

def validar_whatsapp(numero: str) -> bool:
    limpo = re.sub(r"\D", "", numero)
    return 6 <= len(limpo) <= 15

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def salvar_candidatura(dados: dict, video_bytes: bytes, curriculo_bytes: bytes,
                       video_ext: str, curriculo_ext: str) -> bool:
    try:
        candidato_id = str(uuid.uuid4())

        video_path = f"{candidato_id}/video{video_ext}"
        curriculo_path = f"{candidato_id}/curriculo{curriculo_ext}"

        supabase.storage.from_("candidaturas").upload(video_path, video_bytes)
        supabase.storage.from_("candidaturas").upload(curriculo_path, curriculo_bytes)

        video_url = supabase.storage.from_("candidaturas").get_public_url(video_path)
        curriculo_url = supabase.storage.from_("candidaturas").get_public_url(curriculo_path)

        supabase.table("candidatos").insert({
            "id": candidato_id,
            "nome": dados["nome"],
            "email": dados["email"],
            "whatsapp": dados["whatsapp"],
            "cargo": dados["cargo"],
            "video_url": video_url,
            "curriculo_url": curriculo_url,
        }).execute()

        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


# ── Session state init ────────────────────────────────────────────────────────
for key, default in [
    ("etapa", 1),
    ("video_bytes", None),
    ("video_ext", ".webm"),
    ("curriculo_bytes", None),
    ("curriculo_ext", ".pdf"),
    ("dados_pessoais", {}),
    ("cargo", ""),
    ("cargo_outro", ""),
    ("enviado", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:1.5rem 0 .5rem'>
  <span style='font-size:2.8rem'>🎯</span>
  <h1 style='margin:0;color:#1e3a5f'>Formulário de Candidatura</h1>
  <p style='color:#64748b;margin-top:.3rem'>Preencha as etapas abaixo para concluir sua candidatura</p>
</div>
""", unsafe_allow_html=True)

# Barra de progresso
etapa = st.session_state.etapa
progresso = (etapa - 1) / 4
st.progress(progresso, text=f"Etapa {etapa} de 4")

# ════════════════════════════════════════════════════════════════════════════
# ETAPA 1 – Dados pessoais & cargo
# ════════════════════════════════════════════════════════════════════════════
if etapa == 1:
    st.markdown("""
    <div class='card'>
      <span class='step-badge'>Etapa 1 de 4</span>
      <h2>👤 Dados de Contato & Cargo</h2>
    </div>
    """, unsafe_allow_html=True)

    nome = st.text_input("Nome completo *", placeholder="Ex.: Maria da Silva")
    email = st.text_input("E-mail *", placeholder="maria@email.com")

    pais_sel = st.selectbox("País (WhatsApp) *", list(PAISES.keys()))
    ddi = PAISES[pais_sel]
    if pais_sel == "Outro país":
        ddi = st.text_input("DDI do país (ex.: +351)", placeholder="+351")

    whatsapp_num = st.text_input("Número do WhatsApp *", placeholder="(81) 99152-3733")
    whatsapp = f"{ddi} {whatsapp_num}".strip()

    st.divider()

    cargo_sel = st.selectbox("Vaga / Cargo pretendido *", CARGOS)
    cargo_outro = ""
    if cargo_sel == "Outro (digitar abaixo)":
        cargo_outro = st.text_input("Digite o cargo desejado *")

    if st.button("Avançar →", type="primary", use_container_width=True):
        erros = []
        if not nome.strip():
            erros.append("Nome é obrigatório.")
        if not validar_email(email):
            erros.append("E-mail inválido.")
        if not validar_whatsapp(whatsapp):
            erros.append("WhatsApp inválido.")
        if cargo_sel == "Outro (digitar abaixo)" and not cargo_outro.strip():
            erros.append("Informe o cargo desejado.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            cargo_final = cargo_outro.strip() if cargo_sel == "Outro (digitar abaixo)" else cargo_sel
            st.session_state.dados_pessoais = {
                "nome": nome.strip(),
                "email": email.strip(),
                "whatsapp": whatsapp.strip(),
            }
            st.session_state.cargo = cargo_final
            st.session_state.etapa = 2
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ETAPA 2 – Vídeo de apresentação
# ════════════════════════════════════════════════════════════════════════════
elif etapa == 2:
    st.markdown("""
    <div class='card'>
      <span class='step-badge'>Etapa 2 de 4</span>
      <h2>🎥 Vídeo de Apresentação</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box'>
      📌 <strong>Dicas para um bom vídeo:</strong><br>
      • Fale sobre você, sua experiência e qualificações<br>
      • Duração máxima: <strong>2 minutos</strong><br>
      • Você pode regravar quantas vezes quiser antes de avançar<br>
      • Garanta boa iluminação e áudio
    </div>
    """, unsafe_allow_html=True)

    tab_gravar, tab_upload = st.tabs(["🔴 Gravar agora", "📂 Enviar arquivo de vídeo"])

    with tab_gravar:
        st.info("Use o gravador abaixo. Grave, revise e regrave quantas vezes quiser. Quando estiver satisfeito, baixe e envie pela aba ao lado.")

        # Gravação via HTML/JS embutido
        components_html = """
        <div style="font-family:sans-serif">
          <video id="preview" autoplay muted playsinline
            style="width:100%;border-radius:12px;background:#000;max-height:320px"></video>
          <br>
          <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
            <button id="btnStart"
              style="background:#2563eb;color:white;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600">
              ▶ Iniciar Gravação
            </button>
            <button id="btnStop" disabled
              style="background:#dc2626;color:white;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600">
              ⏹ Parar
            </button>
            <button id="btnRegravar" disabled
              style="background:#f59e0b;color:white;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600">
              🔄 Regravar
            </button>
          </div>
          <div id="timer" style="margin-top:8px;font-weight:600;color:#dc2626;font-size:1.1rem"></div>
          <div id="result" style="margin-top:12px"></div>
        </div>

        <script>
        let mr, stream, chunks=[], timerInt, elapsed=0;
        const MAX = 120; // 2 min

        const preview  = document.getElementById('preview');
        const btnStart = document.getElementById('btnStart');
        const btnStop  = document.getElementById('btnStop');
        const timerEl  = document.getElementById('timer');
        const resultEl = document.getElementById('result');

        btnStart.onclick = async () => {
          chunks = []; elapsed = 0;
          resultEl.innerHTML = '';
          stream = await navigator.mediaDevices.getUserMedia({video:true, audio:true});
          preview.srcObject = stream;

          // Contagem regressiva de 5 segundos
          await new Promise(resolve => {
            let count = 5;
            timerEl.textContent = `🎬 Gravando em ${count}...`;
            timerEl.style.color = '#f59e0b';
            const countdown = setInterval(() => {
              count--;
              if(count > 0) {
                timerEl.textContent = `🎬 Gravando em ${count}...`;
              } else {
                clearInterval(countdown);
                timerEl.style.color = '#dc2626';
                resolve();
              }
            }, 1000);
          });

          mr = new MediaRecorder(stream);
          mr.ondataavailable = e => { if(e.data.size) chunks.push(e.data); };
          mr.onstop = () => {
            const blob = new Blob(chunks, {type:'video/webm'});
            const url  = URL.createObjectURL(blob);
            // mostra player de revisão
            resultEl.innerHTML = `
              <p style="color:#15803d;font-weight:600">✅ Gravação concluída! Revise abaixo:</p>
              <video src="${url}" controls style="width:100%;border-radius:10px;max-height:280px"></video>
              <br>
              <button onclick="baixarVideo('${url}')"
                style="display:inline-block;margin-top:12px;background:#16a34a;color:white;
                       padding:10px 24px;border-radius:8px;border:none;cursor:pointer;font-size:15px;font-weight:600">
                ⬇ Baixar vídeo gravado
              </button>
              <script>
              function baixarVideo(url){{
                const a = document.createElement('a');
                a.href = url;
                a.download = 'meu-video.webm';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              }}
              </script>
              <p style="color:#64748b;font-size:13px;margin-top:8px">
                📌 Após baixar, vá para a aba <strong>"Enviar arquivo de vídeo"</strong> e envie o arquivo baixado.
              </p>
            `;
            clearInterval(timerInt);
            timerEl.textContent = '';
            preview.srcObject = null;
          };
          mr.start(1000);
          btnStart.disabled = true;
          btnStop.disabled  = false;
          timerInt = setInterval(() => {
            elapsed++;
            const m = String(Math.floor(elapsed/60)).padStart(2,'0');
            const s = String(elapsed%60).padStart(2,'0');
            timerEl.textContent = `⏱ ${m}:${s} / 02:00`;
            if(elapsed >= MAX) btnStop.click();
          }, 1000);
        };

        const btnRegravar = document.getElementById('btnRegravar');

        btnStop.onclick = () => {
          mr.stop();
          stream.getTracks().forEach(t => t.stop());
          btnStart.disabled   = false;
          btnStop.disabled    = true;
          btnRegravar.disabled = false;
        };

        btnRegravar.onclick = () => {
          resultEl.innerHTML  = '';
          btnRegravar.disabled = true;
          btnStart.click();
        };
        </script>
        """
        st.components.v1.html(components_html, height=520, scrolling=False)

        st.markdown("""
        <div class='info-box' style='margin-top:1rem'>
          💡 Após gravar, <strong>baixe o arquivo</strong> clicando no botão que aparece no player
          e depois <strong>envie-o pela aba "Enviar arquivo de vídeo"</strong> ao lado.
        </div>
        """, unsafe_allow_html=True)

    with tab_upload:
        video_file = st.file_uploader(
            "Selecione o arquivo de vídeo",
            type=["mp4", "webm", "mov", "avi", "mkv"],
            help="Máx. recomendado: 200 MB",
        )
        if video_file:
            st.video(video_file)
            ext = Path(video_file.name).suffix.lower() or ".mp4"
            st.session_state.video_bytes = video_file.read()
            st.session_state.video_ext = ext
            st.success(f"✅ Vídeo carregado: **{video_file.name}** ({len(st.session_state.video_bytes)/1_000_000:.1f} MB)")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.etapa = 1
            st.rerun()
    with col2:
        if st.button("Avançar →", type="primary", use_container_width=True):
            if not st.session_state.video_bytes:
                st.error("Por favor, envie o vídeo antes de avançar.")
            else:
                st.session_state.etapa = 3
                st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ETAPA 3 – Currículo
# ════════════════════════════════════════════════════════════════════════════
elif etapa == 3:
    st.markdown("""
    <div class='card'>
      <span class='step-badge'>Etapa 3 de 4</span>
      <h2>📄 Currículo</h2>
    </div>
    """, unsafe_allow_html=True)

    curriculo_file = st.file_uploader(
        "Anexe seu currículo (PDF ou Word) *",
        type=["pdf", "doc", "docx"],
        help="Formatos aceitos: PDF, DOC, DOCX",
    )

    if curriculo_file:
        ext = Path(curriculo_file.name).suffix.lower()
        st.session_state.curriculo_bytes = curriculo_file.read()
        st.session_state.curriculo_ext = ext
        st.success(f"✅ Currículo carregado: **{curriculo_file.name}**")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.etapa = 2
            st.rerun()
    with col2:
        if st.button("Avançar →", type="primary", use_container_width=True):
            if not st.session_state.curriculo_bytes:
                st.error("Por favor, anexe seu currículo antes de avançar.")
            else:
                st.session_state.etapa = 4
                st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ETAPA 4 – Revisão & Envio
# ════════════════════════════════════════════════════════════════════════════
elif etapa == 4 and not st.session_state.enviado:
    st.markdown("""
    <div class='card'>
      <span class='step-badge'>Etapa 4 de 4</span>
      <h2>✅ Revisão & Envio</h2>
    </div>
    """, unsafe_allow_html=True)

    d = st.session_state.dados_pessoais
    st.markdown(f"""
    <div class='card'>
      <strong>👤 Dados pessoais</strong><br>
      Nome: {d.get('nome','')}<br>
      E-mail: {d.get('email','')}<br>
      WhatsApp: {d.get('whatsapp','')}
      <br><br>
      <strong>🎯 Cargo pretendido:</strong> {st.session_state.cargo}<br>
      <strong>🎥 Vídeo:</strong> {len(st.session_state.video_bytes or b'')/1_000_000:.1f} MB carregado<br>
      <strong>📄 Currículo:</strong> {len(st.session_state.curriculo_bytes or b'')/1_000:.0f} KB carregado
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box'>
      Ao clicar em <strong>Enviar candidatura</strong>, seus dados serão armazenados com segurança
      e nossa equipe de RH entrará em contato em breve.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.etapa = 3
            st.rerun()
    with col2:
        if st.button("🚀 Enviar candidatura", type="primary", use_container_width=True):
            with st.spinner("Enviando... aguarde."):
                ok = salvar_candidatura(
                    dados={**st.session_state.dados_pessoais, "cargo": st.session_state.cargo},
                    video_bytes=st.session_state.video_bytes,
                    curriculo_bytes=st.session_state.curriculo_bytes,
                    video_ext=st.session_state.video_ext,
                    curriculo_ext=st.session_state.curriculo_ext,
                )
            if ok:
                st.session_state.enviado = True
                st.rerun()
            else:
                st.error("Ocorreu um erro. Tente novamente.")

# ════════════════════════════════════════════════════════════════════════════
# SUCESSO
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.enviado:
    st.balloons()
    nome = st.session_state.dados_pessoais.get("nome", "Candidato")
    st.markdown(f"""
    <div class='card' style='text-align:center;padding:3rem'>
      <span style='font-size:4rem'>🎉</span>
      <h2 style='color:#15803d'>Candidatura enviada com sucesso!</h2>
      <p style='font-size:1.1rem'>Olá, <strong>{nome}</strong>!<br>
      Recebemos sua candidatura para a vaga de <strong>{st.session_state.cargo}</strong>.<br>
      Nossa equipe de RH analisará seu perfil e entrará em contato pelo e-mail ou WhatsApp informados.</p>
      <p style='color:#64748b;font-size:.9rem'>Obrigado pelo interesse! 🙌</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📝 Nova candidatura", use_container_width=True):
        for k in ["etapa", "video_bytes", "curriculo_bytes", "dados_pessoais",
                  "cargo", "cargo_outro", "enviado"]:
            del st.session_state[k]
        st.rerun()
