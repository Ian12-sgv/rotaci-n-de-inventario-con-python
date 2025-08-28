def get_query_cruce():
    query = """
-- 1) BODEGA (clasifica por tienda → región y excluye 'Sin region')
WITH BodegaCTE AS (
    SELECT
        LTRIM(RTRIM(di.CodigoBarra)) AS CleanCodigoBarra,
        CASE
            WHEN t.dimID_Tienda IN (2003) THEN 'Valencia Casa Matriz'
            WHEN t.dimID_Tienda IN (2005) THEN 'Oriente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1,1002,1004,1006,1008,1009,1010,1011,1012,
                1013,1014,1017,1018,1019,1020,1021,1022,
                1023,1024,1058
            ) THEN 'Oriente - Sucursales'
            WHEN t.dimID_Tienda IN (2004) THEN 'Occidente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1026,1027,1028,1029,1030,1031,1037,1038,1039,1040,
                1041,1042,1043,1044,1045,1046,1047,1050,1055,2007
            ) THEN 'Occidente - Sucursales'
            ELSE 'Sin region'
        END AS Region,
        SUM(hi.Existencia) AS Existencia_Region
    FROM [BODEGA_DATOS].dbo.tbDimInventario di
    LEFT JOIN [BODEGA_DATOS].dbo.tbHecInventario hi
        ON di.dimID_Inventario = hi.dimid_inventario
    LEFT JOIN [BODEGA_DATOS].dbo.tbDimTiendas t
        ON hi.dimid_tienda = t.dimID_Tienda
    WHERE 1=1
      /*__REF_FILTER__*/   -- usa el MISMO placeholder que ya manejas en Python
    GROUP BY
        LTRIM(RTRIM(di.CodigoBarra)),
        CASE
            WHEN t.dimID_Tienda IN (2003) THEN 'Valencia Casa Matriz'
            WHEN t.dimID_Tienda IN (2005) THEN 'Oriente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1,1002,1004,1006,1008,1009,1010,1011,1012,
                1013,1014,1017,1018,1019,1020,1021,1022,
                1023,1024,1058
            ) THEN 'Oriente - Sucursales'
            WHEN t.dimID_Tienda IN (2004) THEN 'Occidente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1026,1027,1028,1029,1030,1031,1037,1038,1039,1040,
                1041,1042,1043,1044,1045,1046,1047,1050,1055,2007
            ) THEN 'Occidente - Sucursales'
            ELSE 'Sin region'
        END
    HAVING
        CASE
            WHEN t.dimID_Tienda IN (2003) THEN 'Valencia Casa Matriz'
            WHEN t.dimID_Tienda IN (2005) THEN 'Oriente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1,1002,1004,1006,1008,1009,1010,1011,1012,
                1013,1014,1017,1018,1019,1020,1021,1022,
                1023,1024,1058
            ) THEN 'Oriente - Sucursales'
            WHEN t.dimID_Tienda IN (2004) THEN 'Occidente - Casa Matriz'
            WHEN t.dimID_Tienda IN (
                1026,1027,1028,1029,1030,1031,1037,1038,1039,1040,
                1041,1042,1043,1044,1045,1046,1047,1050,1055,2007
            ) THEN 'Occidente - Sucursales'
            ELSE 'Sin region'
        END <> 'Sin region'
),

-- 2) Total de existencia por CódigoBarra
BodegaSum AS (
    SELECT CleanCodigoBarra, SUM(Existencia_Region) AS ExistenciaActual
    FROM BodegaCTE
    GROUP BY CleanCodigoBarra
),

-- 3) Transferencias/Inventario (usa :fechaStart que inyecta Python)
CreacionCTE AS (
    SELECT 
        LTRIM(RTRIM(I.Referencia)) AS CleanReferencia,
        I.CodigoBarra,
        I.CodigoMarca,
        M.Nombre AS Marca,
        I.Nombre,
        COALESCE(F.Nombre, '') AS Nombre_Fabricante,
        COALESCE(F.Codigo, '') AS CodigoFabricante,
        LEFT(C.Codigo, 4) AS CategoriaCodigo,
        C.Nombre AS CategoriaNombre,
        CC.Nombre AS Linea,
        MT.Cantidad AS Cantidad,
        CASE WHEN T.correccion = 1 THEN 1 ELSE 0 END AS correccion,
        MT.Numero AS NumeroTransferencia,
        CAST(T.Fecha AS DATE) AS FechaLlegada,
        COALESCE(T.observacion, '') AS observacion,
        T.CodigoRecibe
    FROM [J101010100_999911].dbo.MOVTRANSFERENCIAS MT
    RIGHT JOIN [J101010100_999911].dbo.INVENTARIO I
        ON I.CodigoBarra = MT.CodigoBarra
    RIGHT JOIN [J101010100_999911].dbo.CATEGORIAS C
        ON I.Categoria = C.Codigo
    LEFT JOIN [J101010100_999911].dbo.MARCAS M
        ON I.CodigoMarca = M.Codigo
    LEFT JOIN [J101010100_999911].dbo.CATEGORIAS CC
        ON LEFT(C.Codigo, 4) = CC.Codigo
    INNER JOIN [J101010100_999911].dbo.TRANSFERENCIAS T
        ON T.numero = MT.numero
    INNER JOIN [J101010100_999911].dbo.FABRICANTES F
        ON F.Codigo = I.Fabricante
    WHERE T.Fecha BETWEEN :fechaStart AND GETDATE()
      AND T.CodigoRecibe = '999999'
      /*__REF_FILTER__*/   -- tu inyección actual (si no hay filtro, Python la borra)
),

-- 4) Agregado base por Código y Fecha
FinalCTE AS (
    SELECT 
        MAX(c.CleanReferencia) AS CleanReferencia,
        c.CodigoBarra,
        MAX(c.CodigoMarca) AS CodigoMarca,
        MAX(c.Marca) AS Marca,
        MAX(c.Nombre) AS Nombre,
        MAX(c.Nombre_Fabricante) AS Nombre_Fabricante,
        MAX(c.CodigoFabricante) AS CodigoFabricante,
        MAX(c.CategoriaCodigo) AS CategoriaCodigo,
        MAX(c.CategoriaNombre) AS CategoriaNombre,
        MAX(c.Linea) AS Linea,
        SUM(CASE WHEN c.Cantidad > 1 THEN c.Cantidad ELSE 0 END) AS CantidadInicial,
        COALESCE(bs.ExistenciaActual, 0) AS ExistenciaActual,
        MAX(c.correccion) AS correccion,
        MAX(c.NumeroTransferencia) AS NumeroTransferencia,
        c.FechaLlegada,
        MAX(c.observacion) AS observacion,
        MAX(c.CodigoRecibe) AS CodigoRecibe
    FROM CreacionCTE c
    LEFT JOIN BodegaSum bs 
        ON LTRIM(RTRIM(c.CodigoBarra)) = bs.CleanCodigoBarra
    WHERE c.Cantidad > 1
    GROUP BY c.CodigoBarra, c.FechaLlegada, bs.ExistenciaActual
),

-- 5) Filtros finales (inyectados desde Python)
FilteredFinal AS (
    SELECT * 
    FROM FinalCTE
    WHERE 1=1 /*__FINAL_FILTERS__*/
),

-- 6) Ventanas y % calculados
Final2 AS (
    SELECT
        f.CleanReferencia,
        f.CodigoBarra,
        f.CodigoMarca,
        f.Marca,
        f.Nombre,
        f.Nombre_Fabricante,
        f.CodigoFabricante,
        f.CategoriaCodigo,
        f.CategoriaNombre,
        f.Linea,
        f.CantidadInicial,
        SUM(f.CantidadInicial) OVER (PARTITION BY f.CodigoBarra) AS Cantidad_Inicial_Agrupada,
        f.ExistenciaActual,
        f.correccion,
        f.NumeroTransferencia,
        f.FechaLlegada,
        f.observacion,
        f.CodigoRecibe,
        CASE 
            WHEN SUM(f.CantidadInicial) OVER (PARTITION BY f.CodigoBarra) = 0 THEN '0%'
            ELSE FORMAT(
                f.ExistenciaActual * 100.0 
                / NULLIF(SUM(f.CantidadInicial) OVER (PARTITION BY f.CodigoBarra), 0),
                'N2'
            ) + '%'
        END AS Queda,
        CASE 
            WHEN SUM(f.CantidadInicial) OVER (PARTITION BY f.CodigoBarra) = 0 THEN '0%'
            ELSE FORMAT(
                100.0 - (
                    f.ExistenciaActual * 100.0 
                    / NULLIF(SUM(f.CantidadInicial) OVER (PARTITION BY f.CodigoBarra), 0)
                ),
                'N2'
            ) + '%'
        END AS Vendido
    FROM FilteredFinal f
)

-- 7) Proyección final
SELECT 
    CleanReferencia AS Referencia,
    CodigoBarra,
    CodigoMarca,
    Marca,
    Nombre,
    Nombre_Fabricante,
    CodigoFabricante,
    CategoriaCodigo,
    CategoriaNombre,
    Linea,
    ISNULL(CantidadInicial, 0)           AS CantidadInicial,
    ISNULL(Cantidad_Inicial_Agrupada, 0) AS Cantidad_Inicial_Agrupada,
    ISNULL(ExistenciaActual, 0)          AS ExistenciaActual,
    correccion,
    NumeroTransferencia,
    FechaLlegada,
    observacion,
    CodigoRecibe,
    Queda,
    Vendido
FROM Final2;
"""
    return query
