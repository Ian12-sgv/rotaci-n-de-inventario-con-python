# db/connection.py
import re
import pandas as pd
from sqlalchemy import create_engine, text
from tkinter import messagebox
from urllib.parse import quote_plus
from queries.query_cruce import get_query_cruce

# ----------------- Configuración de conexión -----------------
DEFAULT_CONNECTION_STR = None

PREDEFINED_INSTANCES = {
    "Servidor DOS": {
        "server_name": "SERVERDOS\\SERVERSQL_DOS",
        "login": "sa",
        "password": "j2094l,."
    },
    "Analista Local": {
        "server_name": "DESKTOP-POHBVL8\\ANALISTA",
        "login": "sa",
        "password": "123456"
    }
}

def set_default_instance(alias):
    """Configura la cadena de conexión usando un alias predefinido."""
    global DEFAULT_CONNECTION_STR
    if alias not in PREDEFINED_INSTANCES:
        raise ValueError(f"Alias '{alias}' no reconocido.")
    config = PREDEFINED_INSTANCES[alias]
    password_enc = quote_plus(config['password'])
    DEFAULT_CONNECTION_STR = (
        f"mssql+pyodbc://{config['login']}:{password_enc}"
        f"@{config['server_name']}/BODEGA_DATOS?driver=SQL+Server"
    )

def get_db_connection(connection_str=None):
    """Retorna una instancia de engine para la conexión a la base de datos."""
    try:
        connection_str = connection_str or DEFAULT_CONNECTION_STR
        if not connection_str:
            raise ValueError("No se ha configurado el connection string.")
        return create_engine(connection_str, pool_size=10, max_overflow=20)
    except Exception as e:
        messagebox.showerror("Error de conexión", f"No se pudo crear el engine: {e}")
        return None

# ----------------- Utilidades de SQL dinámico -----------------
def ensure_final_where(query_base: str, final_alias: str = "Final2") -> str:
    """
    Inserta (si hace falta) un WHERE 1=1 en el bloque que comienza en
    'FROM <final_alias>' y antes de GROUP BY / ORDER BY / HAVING.
    """
    m = re.search(rf"(FROM\s+{re.escape(final_alias)}\b.*)$",
                  query_base, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return query_base.rstrip() + " WHERE 1=1 "

    tail = m.group(1)
    split = re.split(r"\b(GROUP\s+BY|ORDER\s+BY|HAVING)\b",
                     tail, maxsplit=1, flags=re.IGNORECASE)
    head = split[0]
    rest = "" if len(split) == 1 else "".join(split[1:])

    if re.search(r"\bWHERE\b", head, flags=re.IGNORECASE):
        head = head.rstrip() + " "
    else:
        head = head.rstrip() + " WHERE 1=1 "

    return query_base[:m.start()] + head + rest

def _add_excluir_codigorecibe_condition(conditions, params, excluir_codigorecibe, final_alias="Final2"):
    """Agrega NOT IN parametrizado para Final2.CodigoRecibe."""
    if not excluir_codigorecibe:
        return
    codes = [c.strip().upper() for c in excluir_codigorecibe.split(",") if c.strip()]
    if not codes:
        return
    placeholders = []
    for i, c in enumerate(codes):
        key = f"cr_exc_{i}"
        placeholders.append(f":{key}")
        params[key] = c
    clause = f"UPPER(LTRIM(RTRIM({final_alias}.CodigoRecibe))) NOT IN ({', '.join(placeholders)})"
    conditions.append(clause)

def _inject_ref_filter(base_query: str, referencia_filter) -> tuple[str, dict]:
    """
    Reemplaza el marcador /*__REF_FILTER__*/ dentro de CreacionCTE.
    - Si NO hay referencia (None o cadena vacía tras strip), elimina el marcador.
    - Si hay, añade LIKE con :refLike. Si no trae %/_, se asume prefijo (se agrega %).
    """
    marker = "/*__REF_FILTER__*/"
    params = {}
    ref = (referencia_filter or "")
    ref = ref.strip().lower()
    if not ref:
        return base_query.replace(marker, ""), params
    if "%" not in ref and "_" not in ref:
        ref = ref + "%"
    clause = " AND LOWER(LTRIM(RTRIM(I.Referencia))) LIKE :refLike"
    params["refLike"] = ref
    return base_query.replace(marker, clause), params

def _strip_unbound_ref_like(sql: str, params: dict) -> str:
    """
    Si quedó ':refLike' en el SQL pero no existe en params, elimina esa cláusula.
    """
    if "refLike" in params:
        return sql
    pattern = re.compile(
        r"\s+AND\s+LOWER\s*\(\s*LTRIM\s*\(\s*RTRIM\s*\(\s*I\.Referencia\s*\)\s*\)\s*\)\s*LIKE\s*:refLike",
        flags=re.IGNORECASE
    )
    return re.sub(pattern, "", sql)

def _build_full_sql_and_params(
    fecha_option: int,
    codigo_filter=None, referencia_filter=None,
    categoria_filter=None, linea_filter=None, fabrica_filter=None,
    excluir_codigorecibe=None, correccion_solo_01: bool = False
):
    """
    Arma el SQL final y el diccionario de parámetros.
    - :fechaStart se sustituye por literal (evita HY000).
    - La referencia se inyecta dentro de CreacionCTE.
    - El resto de filtros se aplica en el bloque Final2.
    """
    fecha_start = '2023-01-01' if fecha_option == 1 else '2024-01-01'
    sql = get_query_cruce().strip().rstrip(';')

    # Sustituir :fechaStart por literal
    sql = sql.replace(":fechaStart", f"'{fecha_start}'")

    # Inyectar (o quitar) filtro de referencia
    sql, ref_params = _inject_ref_filter(sql, referencia_filter)
    sql = _strip_unbound_ref_like(sql, ref_params)

    # Asegurar WHERE 1=1 en el bloque Final2
    sql = ensure_final_where(sql, "Final2")

    # Filtros finales
    conditions = []
    params: dict[str, object] = {}

    if codigo_filter:
        conditions.append("Final2.CodigoBarra = :codigoFilter")
        params["codigoFilter"] = str(codigo_filter).strip()
    if categoria_filter:
        conditions.append("Final2.CategoriaNombre = :categoriaFilter")
        params["categoriaFilter"] = str(categoria_filter).strip()
    if linea_filter:
        conditions.append("Final2.Linea = :lineaFilter")
        params["lineaFilter"] = str(linea_filter).strip()
    if fabrica_filter:
        conditions.append("Final2.CodigoFabricante = :fabricaFilter")
        params["fabricaFilter"] = str(fabrica_filter).strip()
    if correccion_solo_01:
        conditions.append("Final2.correccion = 0")

    _add_excluir_codigorecibe_condition(conditions, params, excluir_codigorecibe, final_alias="Final2")

    if conditions:
        sql = sql + " AND " + " AND ".join(conditions)

    if not re.search(r"\bORDER\s+BY\b", sql, flags=re.IGNORECASE):
        sql += " ORDER BY Final2.FechaLlegada ASC"

    params.update(ref_params)
    return sql, params

# ----------------- Post-proceso con PIVOT (pandas) -----------------
def _recompute_with_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalcula:
      - Cantidad_Inicial_Agrupada = suma de CantidadInicial por CodigoBarra
        (pivot_table sobre el dataframe ya filtrado).
      - Queda y Vendido a partir de ese total, con formato 'N2' y coma decimal.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else df

    df = df.copy()

    # Asegurar tipos numéricos
    for col in ["CantidadInicial", "ExistenciaActual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- PIVOT: suma por CodigoBarra ---
    # (equivalente: df.groupby('CodigoBarra')['CantidadInicial'].sum())
    pivot = pd.pivot_table(
        df,
        index="CodigoBarra",
        values="CantidadInicial",
        aggfunc="sum",
        fill_value=0
    ).reset_index().rename(columns={"CantidadInicial": "Cantidad_Inicial_Agrupada"})

    # Quitar columna antigua si viene desde SQL y fusionar la nueva
    df = df.drop(columns=["Cantidad_Inicial_Agrupada"], errors="ignore")
    df = df.merge(pivot, on="CodigoBarra", how="left")

    # --- Recalcular Queda/Vendido con el nuevo total ---
    if "ExistenciaActual" in df.columns and "Cantidad_Inicial_Agrupada" in df.columns:
        total = df["Cantidad_Inicial_Agrupada"].replace(0, pd.NA)
        queda = (df["ExistenciaActual"] * 100.0 / total).fillna(0)
        vendido = 100.0 - queda

        def fmt_pct(series: pd.Series) -> pd.Series:
            # Formato 'N2' con coma decimal (p. ej., 33,33%)
            return series.round(2).astype(float).map(lambda v: f"{v:.2f}".replace(".", ",") + "%")

        df["Queda"] = fmt_pct(queda)
        df["Vendido"] = fmt_pct(vendido)

    return df

# ----------------- API públicas -----------------
def get_cruce_data(
    engine,
    codigo_filter=None, referencia_filter=None,
    categoria_filter=None, linea_filter=None, fabrica_filter=None,
    fecha_option=2, excluir_codigorecibe=None, correccion_solo_01: bool = False
):
    """Ejecuta el query con filtros y devuelve lista de dicts (post-procesado con pivot)."""
    full_sql, params = _build_full_sql_and_params(
        fecha_option=fecha_option,
        codigo_filter=codigo_filter,
        referencia_filter=referencia_filter,
        categoria_filter=categoria_filter,
        linea_filter=linea_filter,
        fabrica_filter=fabrica_filter,
        excluir_codigorecibe=excluir_codigorecibe,
        correccion_solo_01=correccion_solo_01,
    )
    with engine.connect() as conn:
        rows = conn.execute(text(full_sql), params).fetchall()

    df = pd.DataFrame([dict(r._mapping) for r in rows])
    df = _recompute_with_pivot(df)
    return df.to_dict(orient="records")

def get_cruce_data_df(
    engine,
    codigo_filter=None, referencia_filter=None,
    categoria_filter=None, linea_filter=None, fabrica_filter=None,
    fecha_option=2, chunksize=50000, excluir_codigorecibe=None,
    correccion_solo_01: bool = False
):
    """Devuelve DataFrame con los mismos filtros (post-procesado con pivot)."""
    full_sql, params = _build_full_sql_and_params(
        fecha_option=fecha_option,
        codigo_filter=codigo_filter,
        referencia_filter=referencia_filter,
        categoria_filter=categoria_filter,
        linea_filter=linea_filter,
        fabrica_filter=fabrica_filter,
        excluir_codigorecibe=excluir_codigorecibe,
        correccion_solo_01=correccion_solo_01,
    )
    df_iter = pd.read_sql(text(full_sql), con=engine, params=params, chunksize=chunksize)
    df = pd.concat(df_iter, ignore_index=True)
    return _recompute_with_pivot(df)
