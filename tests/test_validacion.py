
import csv
import hashlib

import pytest

from scripts.validar_datos import (
    COLUMNAS,
    ErrorValidacion,
    validar_archivo,
    verificar_integridad,
)

REGISTRO_VALIDO = {
    "InvoiceNo": "536365",
    "StockCode": "85123A",
    "Description": "WHITE HANGING HEART",
    "InvoiceDate": "2011-10-15 09:30:00",
    "Quantity": "6",
    "UnitPrice": "2.55",
    "lote": "control",
}


def crear_csv(tmp_path, registros, columnas=None):

    if columnas is None:
        columnas = COLUMNAS

    ruta = tmp_path / "prueba.csv"

    with ruta.open(
        "w", encoding="utf-8", newline=""
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas,
            extrasaction="ignore",
        )

        escritor.writeheader()
        escritor.writerows(registros)

    return ruta


# 1. Archivos validos para los tres periodos.

@pytest.mark.parametrize(
    "lote,fecha",
    [
        ("referencia", "2011-09-15 10:00:00"),
        ("control", "2011-10-15 10:00:00"),
        ("nuevo", "2011-11-15 10:00:00"),
    ],
)
def test_archivo_valido(tmp_path, lote, fecha):

    registro = {
        **REGISTRO_VALIDO,
        "lote": lote,
        "InvoiceDate": fecha,
    }

    ruta = crear_csv(tmp_path, [registro])

    resultado = validar_archivo(ruta, {lote})

    assert resultado["valido"] is True
    assert resultado["filas"] == 1
    assert resultado["lote"] == lote


# 2. Encabezado faltante.

def test_encabezado_faltante(tmp_path):

    columnas = [
        c for c in COLUMNAS if c != "Quantity"
    ]

    ruta = crear_csv(
        tmp_path, [REGISTRO_VALIDO], columnas
    )

    with pytest.raises(
        ErrorValidacion, match="Encabezados"
    ):
        validar_archivo(ruta, {"control"})


# 3. Encabezado adicional.

def test_encabezado_adicional(tmp_path):

    columnas = COLUMNAS + ["Extra"]

    ruta = crear_csv(
        tmp_path, [REGISTRO_VALIDO], columnas
    )

    with pytest.raises(
        ErrorValidacion, match="Encabezados"
    ):
        validar_archivo(ruta, {"control"})


# 4. Encabezado duplicado.

def test_encabezado_duplicado(tmp_path):

    columnas = COLUMNAS[:-1] + ["Quantity"]

    ruta = crear_csv(
        tmp_path, [REGISTRO_VALIDO], columnas
    )

    with pytest.raises(
        ErrorValidacion, match="Encabezados"
    ):
        validar_archivo(ruta, {"control"})


# 5. Campos de texto vacios.

@pytest.mark.parametrize(
    "campo,valor",
    [
        ("InvoiceNo", ""),
        ("StockCode", ""),
        ("Description", ""),
        ("Description", "   "),
    ],
)
def test_campo_vacio(tmp_path, campo, valor):

    registro = {
        **REGISTRO_VALIDO,
        campo: valor,
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match=campo
    ):
        validar_archivo(ruta, {"control"})


# 6. Fechas imposibles o con formato incorrecto.

@pytest.mark.parametrize(
    "fecha",
    [
        "2011-11-31 09:00:00",
        "2011-02-29 09:00:00",
        "2011-10-15 25:00:00",
        "2011-10-15 09:70:00",
        "15/10/2011 09:00:00",
        "2011-10-5 09:00:00",
        "2011-10-15",
        "",
    ],
)
def test_fecha_invalida(tmp_path, fecha):

    registro = {
        **REGISTRO_VALIDO,
        "InvoiceDate": fecha,
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="InvoiceDate"
    ):
        validar_archivo(ruta, {"control"})


# 7. Cantidades invalidas.

@pytest.mark.parametrize(
    "cantidad",
    ["0", "-5", "2.5", "abc", "", "NaN"],
)
def test_cantidad_invalida(tmp_path, cantidad):

    registro = {
        **REGISTRO_VALIDO,
        "Quantity": cantidad,
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="Quantity"
    ):
        validar_archivo(ruta, {"control"})


# 8. Precios invalidos.

@pytest.mark.parametrize(
    "precio",
    ["0", "-2.55", "abc", "NaN", "inf", "-inf", ""],
)
def test_precio_invalido(tmp_path, precio):

    registro = {
        **REGISTRO_VALIDO,
        "UnitPrice": precio,
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="UnitPrice"
    ):
        validar_archivo(ruta, {"control"})


# 9. Facturas repetidas permitidas.

def test_factura_repetida(tmp_path):

    segundo_registro = {
        **REGISTRO_VALIDO,
        "StockCode": "12345B",
        "Description": "SECOND PRODUCT",
    }

    ruta = crear_csv(
        tmp_path,
        [REGISTRO_VALIDO, segundo_registro],
    )

    resultado = validar_archivo(ruta, {"control"})

    assert resultado["valido"] is True
    assert resultado["filas"] == 2


# 10. Archivo inexistente.

def test_archivo_inexistente(tmp_path):

    ruta = tmp_path / "no_existe.csv"

    with pytest.raises(
        ErrorValidacion, match="no existe"
    ):
        validar_archivo(ruta, {"control"})


# 11. Archivo con encabezados y sin registros.

def test_archivo_sin_registros(tmp_path):

    ruta = crear_csv(tmp_path, [])

    with pytest.raises(
        ErrorValidacion, match="al menos una fila"
    ):
        validar_archivo(ruta, {"control"})


# 12. Archivo completamente vacio.

def test_archivo_vacio(tmp_path):

    ruta = tmp_path / "vacio.csv"
    ruta.write_text("", encoding="utf-8")

    with pytest.raises(
        ErrorValidacion, match="vacio"
    ):
        validar_archivo(ruta, {"control"})


# 13. Lote no permitido.

def test_lote_incorrecto(tmp_path):

    registro = {
        **REGISTRO_VALIDO,
        "lote": "desconocido",
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="Lote no permitido"
    ):
        validar_archivo(ruta, {"control", "nuevo"})


# 14. Mezcla de dos lotes.

def test_lotes_mezclados(tmp_path):

    segundo_registro = {
        **REGISTRO_VALIDO,
        "lote": "nuevo",
        "InvoiceDate": "2011-11-15 09:00:00",
    }

    ruta = crear_csv(
        tmp_path,
        [REGISTRO_VALIDO, segundo_registro],
    )

    with pytest.raises(
        ErrorValidacion, match="mezclar"
    ):
        validar_archivo(ruta, {"control", "nuevo"})


# 15. Mes incorrecto para el lote.

def test_mes_incorrecto(tmp_path):

    registro = {
        **REGISTRO_VALIDO,
        "InvoiceDate": "2011-11-15 09:00:00",
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="no corresponde"
    ):
        validar_archivo(ruta, {"control"})


# 16. Anio incorrecto para el lote.

def test_anio_incorrecto(tmp_path):

    registro = {
        **REGISTRO_VALIDO,
        "InvoiceDate": "2012-10-15 09:00:00",
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="no corresponde"
    ):
        validar_archivo(ruta, {"control"})


# 17. Referencia integra.

def test_integridad_correcta(tmp_path):

    ruta = crear_csv(tmp_path, [REGISTRO_VALIDO])

    hash_esperado = hashlib.sha256(
        ruta.read_bytes()
    ).hexdigest()

    assert (
        verificar_integridad(ruta, hash_esperado)
        == hash_esperado
    )


# 18. Referencia modificada.

def test_integridad_modificada(tmp_path):

    ruta = crear_csv(tmp_path, [REGISTRO_VALIDO])

    hash_esperado = hashlib.sha256(
        ruta.read_bytes()
    ).hexdigest()

    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write("MODIFICADO")

    with pytest.raises(
        ErrorValidacion, match="modificado"
    ):
        verificar_integridad(ruta, hash_esperado)

# 19. Fila con campos faltantes.

def test_fila_incompleta(tmp_path):

    ruta = crear_csv(tmp_path, [REGISTRO_VALIDO])

    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write("12345,ABC,PRODUCTO\n")

    with pytest.raises(
        ErrorValidacion, match="siete campos"
    ):
        validar_archivo(ruta, {"control"})


# 20. Archivo con codificacion invalida.

def test_codificacion_invalida(tmp_path):

    ruta = tmp_path / "codificacion.csv"

    ruta.write_bytes(b"\xff\xfe\xff")

    with pytest.raises(
        ErrorValidacion, match="No se pudo leer"
    ):
        validar_archivo(ruta, {"control"})


# 21. CSV mal formado.

def test_csv_mal_formado(tmp_path):

    ruta = tmp_path / "malformado.csv"

    ruta.write_text(
        ",".join(COLUMNAS) + '\n"campo sin cerrar',
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorValidacion, match="No se pudo leer"
    ):
        validar_archivo(ruta, {"control"})


# 22. Precio con formato incorrecto.

def test_formato_precio_incorrecto(tmp_path):

    registro = {
        **REGISTRO_VALIDO,
        "UnitPrice": "1_000",
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="Formato numerico"
    ):
        validar_archivo(ruta, {"control"})


# 23. Cantidad excesivamente grande.

def test_cantidad_fuera_de_rango(tmp_path):

    registro = {
        **REGISTRO_VALIDO,
        "Quantity": "9" * 5000,
    }

    ruta = crear_csv(tmp_path, [registro])

    with pytest.raises(
        ErrorValidacion, match="Cantidad fuera"
    ):
        validar_archivo(ruta, {"control"})


# 24. Ejecucion completa del validador.

@pytest.mark.parametrize("datos_validos", [True, False])
def test_main_integracion(
    tmp_path, monkeypatch, capsys, datos_validos
):

    from scripts import validar_datos as validador

    registro_referencia = {
        **REGISTRO_VALIDO,
        "lote": "referencia",
        "InvoiceDate": "2011-09-15 09:00:00",
    }

    ruta_referencia = crear_csv(
        tmp_path, [registro_referencia]
    )

    ruta_referencia = ruta_referencia.rename(
        tmp_path / "referencia.csv"
    )

    registro_actual = dict(REGISTRO_VALIDO)

    if not datos_validos:
        registro_actual["InvoiceDate"] = (
            "2011-11-31 09:00:00"
        )

    ruta_actual = crear_csv(
        tmp_path, [registro_actual]
    )

    ruta_actual.rename(tmp_path / "actual.csv")

    hash_referencia = hashlib.sha256(
        ruta_referencia.read_bytes()
    ).hexdigest()

    funcion_integridad = validador.verificar_integridad

    monkeypatch.setattr(
        validador,
        "DATA_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        validador,
        "verificar_integridad",
        lambda ruta: funcion_integridad(
            ruta, hash_referencia
        ),
    )

    resultado = validador.main()

    salida = capsys.readouterr().out

    if datos_validos:

        assert resultado == 0
        assert "Todos los datos son validos" in salida
        assert "Integridad de referencia verificada" in salida

    else:

        assert resultado == 1
        assert "VALIDACION FALLIDA" in salida
        assert "InvoiceDate" in salida
        assert "BLOQUEADO" in salida
