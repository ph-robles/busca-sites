# utils/data_loader.py
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Optional, Set

EXCEL_PATH = Path("enderecos.xlsx")

# =========================================================
#  Helpers
# =========================================================

def _to_numeric_series(s: pd.Series) -> pd.Series:
    """
    Converte a série para float de forma segura:
    - Normaliza vírgula para ponto
    - Converte texto inválido para NaN (sem levantar exceção)
    Resultado: dtype float64 com NaN (np.nan) onde inválido.
    """
    if s is None:
        return pd.Series(dtype="float64")
    s2 = (
        s.astype(str)
         .str.strip()
         .str.replace(",", ".", regex=False)
         .replace({"": None, "nan": None, "None": None, "-": None, "—": None})
    )
    # Converte qualquer coisa não numérica para NaN
    return pd.to_numeric(s2, errors="coerce")


def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Acha coluna por nome exato (case-insensitive) ou contendo o termo."""
    if df is None or df.empty:
        return None
    cols_lc_map = {c.lower(): c for c in df.columns}
    # Match exato
    for cand in candidates:
        key = cand.lower()
        if key in cols_lc_map:
            return cols_lc_map[key]
    # Match contendo
    for c in df.columns:
        lc = c.lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None


# =========================================================
#  Carregador principal — Aba ENDERECOS
# =========================================================

@st.cache_data(show_spinner=False)
def carregar_dados() -> pd.DataFrame:
    """
    Lê 'enderecos.xlsx' > aba 'enderecos'
    Normaliza colunas para:
      sigla, nome, endereco, detentora, lat, lon, capacitado
    Trata coordenadas inválidas convertendo-as para NaN (sem erro).
    """
    # ---------- Arquivo existe? ----------
    if not EXCEL_PATH.exists():
        st.error("❌ Arquivo `enderecos.xlsx` não foi encontrado na raiz do projeto.")
        st.stop()

    # ---------- Ler aba principal ----------
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="enderecos", engine="openpyxl")
    except ValueError:
        st.error("❌ A aba **enderecos** não existe no arquivo.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao ler o Excel: {e}")
        st.stop()

    if df is None or df.empty:
        st.error("❌ A aba `enderecos` está vazia.")
        st.stop()

    df.columns = df.columns.astype(str).str.strip().str.lower()

    # ---------- Detectar colunas ----------
    col_sig = _find_col(df, ["sigla", "sigla_da_torre"])
    col_nome = _find_col(df, ["nome", "nome_da_torre"])
    col_end  = _find_col(df, ["endereco", "endereço"])
    col_det  = _find_col(df, ["detentora"])
    col_lat  = _find_col(df, ["lat", "latitude"])
    col_lon  = _find_col(df, ["lon", "longitude"])
    col_cap  = _find_col(df, ["capacitado", "habilitado", "ativo", "status"])

    missing = []
    if not col_sig: missing.append("sigla (ex.: sigla / sigla_da_torre)")
    if not col_nome: missing.append("nome (ex.: nome / nome_da_torre)")
    if not col_end:  missing.append("endereco (ex.: endereço / endereco)")
    if not col_lat:  missing.append("lat (ex.: lat / latitude)")
    if not col_lon:  missing.append("lon (ex.: lon / longitude)")

    if missing:
        st.error(
            "❌ Colunas essenciais ausentes na aba `enderecos`:\n\n" +
            "\n".join(f"- {m}" for m in missing) +
            "\n\n👉 Verifique os nomes das colunas na planilha."
        )
        st.write("Colunas detectadas no arquivo:", list(df.columns))
        st.stop()

    # ---------- Construção final ----------
    out = pd.DataFrame()
    out["sigla"]     = df[col_sig].astype("string").str.strip()
    out["nome"]      = df[col_nome].astype("string").str.strip()
    out["endereco"]  = df[col_end].astype("string").str.strip()
    out["detentora"] = (df[col_det].astype("string").str.strip() if col_det else pd.Series(pd.NA, index=df.index))
    out["capacitado"] = (df[col_cap].astype("string").str.strip() if col_cap else pd.Series(pd.NA, index=df.index))

    # ---------- Coordenadas seguras (sem TypeError) ----------
    out["lat"] = _to_numeric_series(df[col_lat])  # float64 + NaN onde inválido
    out["lon"] = _to_numeric_series(df[col_lon])  # float64 + NaN onde inválido

    return out


# =========================================================
#  Carregar acessos (se existir)
# =========================================================

@st.cache_data(show_spinner=False)
def carregar_acessos() -> Optional[pd.DataFrame]:
    """
    Lê aba 'acessos', detecta colunas e filtra status 'ok' (quando existir).
    Retorna DataFrame com colunas: sigla, tecnico. Ou None.
    """
    if not EXCEL_PATH.exists():
        return None

    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="acessos", engine="openpyxl")
    except ValueError:
        return None
    except Exception:
        return None

    if df is None or df.empty:
        return None

    df.columns = df.columns.astype(str).str.strip().str.lower()

    col_sig = _find_col(df, ["sigla", "sigla_da_torre", "site", "torre"])
    col_tec = _find_col(df, ["tecnico", "técnico", "colaborador", "nome_tecnico"])
    col_sta = _find_col(df, ["status", "situacao", "situação"])

    if not col_sig or not col_tec:
        return None

    df_out = pd.DataFrame()
    df_out["sigla"]   = df[col_sig].astype("string").str.strip()
    df_out["tecnico"] = df[col_tec].astype("string").str.strip()

    if col_sta:
        mask_ok = (
            df[col_sta].astype(str).str.strip().str.lower()
            .isin(["ok", "liberado", "aprovado", "ativo"])
        )
        df_out = df_out[mask_ok]

    df_out = df_out.dropna(subset=["sigla", "tecnico"]).reset_index(drop=True)
    return df_out if not df_out.empty else None


# =========================================================
#  (Opcional) Lista de SIGLAs capacitados em aba separada
# =========================================================

@st.cache_data(show_spinner=False)
def carregar_capacitados_lista() -> Optional[Set[str]]:
    """
    Procura abas: 'capacitados', 'capacitacao', 'cap_ativos'
    Aceita colunas: 'sigla' e opcional 'status/capacitado/ativo'
    Retorna set de SIGLAs em uppercase ou None.
    """
    if not EXCEL_PATH.exists():
        return None

    candidate_sheets = ["capacitados", "capacitacao", "cap_ativos"]
    for sh in candidate_sheets:
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=sh, engine="openpyxl")
        except ValueError:
            continue
        except Exception:
            continue

        if df is None or df.empty:
            continue

        df.columns = df.columns.astype(str).str.strip().str.lower()
        col_sig = _find_col(df, ["sigla", "sigla_da_torre", "site", "torre"])
        col_sta = _find_col(df, ["status", "capacitado", "ativo", "habilitado"])

        if not col_sig:
            continue

        df = df.dropna(subset=[col_sig]).copy()
        df[col_sig] = df[col_sig].astype(str).str.strip()

        if col_sta:
            mask = df[col_sta].astype(str).str.strip().str.lower().isin(
                ["sim", "yes", "y", "true", "ok", "ativo", "habilitado", "cap", "capacitad", "1"]
            )
            sigs = df.loc[mask, col_sig].str.upper().unique().tolist()
        else:
            sigs = df[col_sig].str.upper().unique().tolist()

        if sigs:
            return set(sigs)

    return None
