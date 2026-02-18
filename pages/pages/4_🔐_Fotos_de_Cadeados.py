import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import io
import secrets
import mimetypes

from utils.data_loader import carregar_dados

# ========== Config da página ==========
st.set_page_config(page_title="Fotos de Cadeados • Site Radar", page_icon="🔐", layout="wide")

# ========== Sidebar premium compacta ==========
sidebar_style = """
<style>
[data-testid="stSidebar"] {
    background: rgba(20, 25, 35, 0.55) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 40px;
    width: 240px !important;
}
.sidebar-logo { display:flex; justify-content:center; margin-bottom:30px; }

@media (max-width: 760px) {
    [data-testid="stSidebar"] {
        width: 80px !important;
        min-width: 80px !important;
        padding-top: 24px;
        padding-left: 6px;
        padding-right: 6px;
    }
    .sidebar-logo img { width: 60px !important; }
    .sidebar-content, .sidebar-text { display: none !important; }
}

.card {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.7);
}
:root .st-dark .card {
  background: rgba(0,0,0,0.15);
  border-color: rgba(255,255,255,0.15);
}
</style>
"""
st.markdown(sidebar_style, unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    st.image("logo.png", width=130)
    st.markdown("</div>", unsafe_allow_html=True)

# ========== Helpers ==========
def supabase_client():
    """Inicializa Supabase se secrets estiverem definidos; senão retorna None."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if url and key:
        try:
            from supabase import create_client
            return create_client(url, key)
        except Exception as e:
            st.warning(f"Supabase não pôde ser inicializado: {e}")
            return None
    return None

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p

def guess_mime(filename: str, default="application/octet-stream"):
    mt, _ = mimetypes.guess_type(filename)
    return mt or default

def safe_filename(sigla: str, original_name: str):
    base = os.path.basename(original_name)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    rand = secrets.token_hex(3)  # 6 hex chars
    # remove espaços e caracteres problemáticos
    base = base.replace(" ", "_")
    return f"{sigla}_{ts}_{rand}_{base}"

# ========== Carrega dados ==========
df = carregar_dados()
siglas = sorted(df["sigla"].dropna().astype(str).str.upper().unique().tolist())

st.title("🔐 Fotos de cadeados (por SIGLA)")

# ========== Formulário ==========
with st.form("form_fotos", clear_on_submit=False):
    col1, col2 = st.columns([2, 1])
    with col1:
        sigla_sel = st.selectbox("SIGLA", options=siglas, index=None, placeholder="Digite para buscar…")
    with col2:
        ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("Data/hora", value=ts_now, disabled=True)

    # Tipos de cadeado frequentes (exemplos práticos — personalize livremente)
    tipos = [
        "Tetra", "Papaiz", "Pado", "Multiponto", "Yale/Chave comum",
        "Catraca", "Cadeado com corrente", "Outro"
    ]
    lock_type = st.selectbox("Tipo de cadeado", options=tipos, index=0)
    lock_type_outro = ""
    if lock_type == "Outro":
        lock_type_outro = st.text_input("Qual?", placeholder="Descreva o tipo de cadeado")

    notes = st.text_area("Observações", placeholder="Ex.: cadeado enferrujado, difícil de abrir, sem identificação...")

    up = st.file_uploader(
        "Envie a foto do cadeado",
        type=["png", "jpg", "jpeg", "webp", "heic", "heif"],
        accept_multiple_files=False
    )

    submitted = st.form_submit_button("Salvar foto (OK)")

# ========== Processa upload ==========
DATA_DIR = ensure_dir(Path("data"))
LOCKS_DIR = ensure_dir(DATA_DIR / "locks")
CSV_PATH = DATA_DIR / "locks.csv"

client = supabase_client()
bucket = st.secrets.get("SUPABASE_BUCKET", "site-locks")
table_name = st.secrets.get("SUPABASE_TABLE", None)

def save_metadata_local(row: dict):
    df_new = pd.DataFrame([row])
    if CSV_PATH.exists():
        df_new.to_csv(CSV_PATH, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df_new.to_csv(CSV_PATH, mode="w", header=True, index=False, encoding="utf-8")

def save_metadata_supabase(row: dict):
    if not client or not table_name:
        return None
    try:
        res = client.table(table_name).insert(row).execute()
        return res
    except Exception as e:
        st.warning(f"Não foi possível inserir metadados na tabela '{table_name}': {e}")
        return None

def upload_to_supabase(sigla: str, file_name: str, file_bytes: bytes, mime: str) -> str | None:
    if not client:
        return None
    try:
        path = f"{sigla}/{file_name}"
        # upload
        client.storage.from_(bucket).upload(
            file=file_bytes,
            path=path,
            file_options={"content-type": mime, "upsert": False}
        )
        # public URL
        public_url = client.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as e:
        st.warning(f"Upload no Supabase falhou: {e}")
        return None

def upload_local(sigla: str, file_name: str, file_bytes: bytes) -> str:
    dir_sigla = ensure_dir(LOCKS_DIR / sigla)
    dest = dir_sigla / file_name
    with open(dest, "wb") as f:
        f.write(file_bytes)
    # URL local “simulada” (exibição no Streamlit via st.image)
    return str(dest)  # caminho local

if submitted:
    if not sigla_sel:
        st.error("Selecione a **SIGLA**.")
    elif up is None:
        st.error("Envie uma **foto** do cadeado.")
    else:
        st.toast("Processando upload…", icon="⏳")
        # consolidar tipo
        lock_final = lock_type_outro.strip() if lock_type == "Outro" else lock_type

        # prepara bytes e nome final
        file_bytes = up.read()
        final_name = safe_filename(sigla_sel, up.name)
        mime = guess_mime(up.name, "image/jpeg")

        # Tenta nuvem (Supabase); se falhar, salva local
        public_url = upload_to_supabase(sigla_sel, final_name, file_bytes, mime)
        if not public_url:
            # fallback local
            public_url = upload_local(sigla_sel, final_name, file_bytes)

        # monta metadados
        row = {
            "timestamp": ts_now,
            "sigla": sigla_sel,
            "lock_type": lock_final,
            "notes": notes,
            "photo_url": public_url,
            "uploaded_by": st.session_state.get("user", "tecnico")  # se quiser capturar um nome depois
        }

        # salva metadados (local SEMPRE; supabase TABELA se configurado)
        try:
            save_metadata_local(row)
        except Exception as e:
            st.warning(f"Não foi possível salvar metadados localmente (CSV): {e}")

        save_metadata_supabase(row)  # ignora erros silenciosamente (já avisado no warn)

        st.success("✅ Foto salva com sucesso!")
        st.session_state["last_upload_sigla"] = sigla_sel

# ========== Galeria recente por SIGLA ==========
st.markdown("### 🖼️ Últimas fotos da SIGLA")

sig_ref = sigla_sel or st.session_state.get("last_upload_sigla", None)
if not sig_ref:
    st.info("Selecione uma SIGLA para ver a galeria.")
else:
    # tenta ler do Supabase table; senão do CSV; senão do diretório local
    rows = []
    used_source = None
    if client and table_name:
        try:
            res = (
                client.table(table_name)
                .select("timestamp,sigla,lock_type,notes,photo_url")
                .eq("sigla", sig_ref)
                .order("timestamp", desc=True)
                .limit(12)
                .execute()
            )
            data = res.data or []
            rows = data
            used_source = "supabase_table"
        except Exception:
            rows = []

    if not rows and CSV_PATH.exists():
        try:
            df_meta = pd.read_csv(CSV_PATH, encoding="utf-8")
            df_meta = df_meta[df_meta["sigla"].astype(str).str.upper() == sig_ref]
            df_meta = df_meta.sort_values("timestamp", ascending=False).head(12)
            rows = df_meta.to_dict(orient="records")
            used_source = "csv_local"
        except Exception:
            rows = []

    # fallback “lista por diretório” (pode não ter metadados)
    if not rows:
        dir_sigla = LOCKS_DIR / sig_ref
        if dir_sigla.exists():
            files = sorted(dir_sigla.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
            rows = [{"timestamp": "", "sigla": sig_ref, "lock_type": "", "notes": "", "photo_url": str(p)} for p in files]
            used_source = "dir_local"

    if not rows:
        st.info("Nenhuma foto encontrada para esta SIGLA (ainda).")
    else:
        cols = st.columns(3)
        for i, r in enumerate(rows):
            with cols[i % 3]:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                # se URL for local, usa st.image; se for pública, também funciona
                # Streamlit lida com URL http(s) ou caminho local
                st.image(r["photo_url"], use_column_width=True)
                caption = f"**{r.get('lock_type','')}** — {r.get('timestamp','')}"
                if r.get("notes"):
                    caption += f"\n\n*{r['notes']}*"
                st.caption(caption)
                st.markdown('</div>', unsafe_allow_html=True)
``
