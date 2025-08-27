import re
import pandas as pd
from sqlalchemy import create_engine, text
from tkinter import messagebox
from urllib.parse import quote_plus
from queries.query_cruce import get_query_cruce

# Variable global para el connection string
DEFAULT_CONNECTION_STR = None

# Instancias predefinidas (solo estas se permiten)
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
        f"mssql+pyodbc://{config['login']}:{password_enc}@{config['server_name']}/BODEGA_DATOS?driver=SQL+Server"
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

def ensure_final_where(query_base: str, final_alias: str = "Final2", marker: str = "/*__FILTROS__*/") -> str:
    """
    Inserta (si hace falta) un WHERE 1=1 y un marcador para filtros en el bloque que
    comienza en 'FROM <final_alias>' y antes de GROUP BY / ORDER BY / HAVING.
    """
    m = re.search(rf"(FROM\s+{re.escape(final_alias)}\b.*)$", query_base, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return query_base.rstrip() + f" WHERE 1=1 {marker}"
    tail = m.group(1)
    split = re.split(r"\b(GROUP\s+BY|ORDER\s+BY|HAVING)\b", tail, maxsplit=1, flags=re.IGNORECASE)
    head = split[0]
    rest = "" if len(split) == 1 else "".join(split[1:])
    if re.search(r"\bWHERE\b", head, flags=re.IGNORECASE):
        head = head.rstrip() + " " + marker + " "
    else:
        head = head.rstrip() + f" WHERE 1=1 {marker} "
    return query_base[:m.start()] + head + rest

def _build_full_sql(fecha_option: int,
                    codigo_filter=None, referencia_filter=None,
                    categoria_filter=None, linea_filter=None, fabrica_filter=None,
                    final_alias: str = "Final2",
                    marker: str = "/*__FILTROS__*/"):

    # 1) Fecha literal (no parámetro) para evitar desajustes de marcadores
    fecha_start = '2023-01-01' if fecha_option == 1 else '2024-01-01'
    fecha_literal = f"CAST('{fecha_start}' AS date)"  # o CONVERT(date, 'YYYY-MM-DD', 23)

    # 2) Base del query
    base_query = get_query_cruce().strip().rstrip(';')

    # Reemplaza cualquier :fechaStart que exista en la CTE por el literal
    # (si tu query_cruce no lo usa, esto no afecta).
    base_query = base_query.replace(":fechaStart", f"'{fecha_start}'")

    # Inserta WHERE/marker en el bloque del alias final
    base_query = ensure_final_where(base_query, final_alias=final_alias, marker=marker)

    # 3) Filtros (la fecha final se inyecta como literal, no parámetro)
    conditions = [f"{final_alias}.FechaLlegada >= {fecha_literal}"]

    params = {}
    if codigo_filter:
        conditions.append("CodigoBarra = :codigoFilter")
        params["codigoFilter"] = codigo_filter
    if referencia_filter:
        conditions.append(f"LOWER(LTRIM(RTRIM({final_alias}.CleanReferencia))) = :referenciaFilter")
        params["referenciaFilter"] = referencia_filter.strip().lower()
    if categoria_filter:
        conditions.append("CategoriaNombre = :categoriaFilter")
        params["categoriaFilter"] = categoria_filter
    if linea_filter:
        conditions.append("Linea = :lineaFilter")
        params["lineaFilter"] = linea_filter
    if fabrica_filter:
        conditions.append("CodigoFabricante = :fabricaFilter")
        params["fabricaFilter"] = fabrica_filter

    filter_clause = " AND " + " AND ".join(conditions) if conditions else ""
    full_sql = base_query.replace(marker, filter_clause)

    # 4) ORDER BY si no existe ya
    if not re.search(r"\bORDER\s+BY\b", full_sql, flags=re.IGNORECASE):
        full_sql += f" ORDER BY {final_alias}.FechaLlegada ASC"

    return full_sql, params

def get_cruce_data(engine, codigo_filter=None, referencia_filter=None,
                   categoria_filter=None, linea_filter=None, fabrica_filter=None,
                   fecha_option=2):
    """Ejecuta el query de cruce con filtros y retorna lista de diccionarios."""
    full_sql, params = _build_full_sql(
        fecha_option=fecha_option,
        codigo_filter=codigo_filter,
        referencia_filter=referencia_filter,
        categoria_filter=categoria_filter,
        linea_filter=linea_filter,
        fabrica_filter=fabrica_filter,
        final_alias="Final2",
        marker="/*__FILTROS__*/"
    )
    with engine.connect() as conn:
        result = conn.execute(text(full_sql), params).fetchall()
    return [dict(row._mapping) for row in result]

def get_cruce_data_df(engine, codigo_filter=None, referencia_filter=None,
                      categoria_filter=None, linea_filter=None, fabrica_filter=None,
                      fecha_option=2, chunksize=50000):
    """Versión para Pandas DataFrame."""
    full_sql, params = _build_full_sql(
        fecha_option=fecha_option,
        codigo_filter=codigo_filter,
        referencia_filter=referencia_filter,
        categoria_filter=categoria_filter,
        linea_filter=linea_filter,
        fabrica_filter=fabrica_filter,
        final_alias="Final2",
        marker="/*__FILTROS__*/"
    )
    df_iter = pd.read_sql(text(full_sql), con=engine, params=params, chunksize=chunksize)
    return pd.concat(df_iter, ignore_index=True)
