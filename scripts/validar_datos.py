
import csv
import hashlib
import math
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "datos"

COLUMNAS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "InvoiceDate",
    "Quantity",
    "UnitPrice",
    "lote",
]

PERIODOS = {
    "referencia": (2011, 9),
    "control": (2011, 10),
    "nuevo": (2011, 11),
}

HASH_REFERENCIA = (
    "4035fa80c4d52db29389f156ca9fe4e251"
    "f9d4fb8d61e665b7177ea2766842cf"
)

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


class ErrorValidacion(ValueError):
    """Error de calidad de datos."""


def error(ruta, fila, campo, valor, motivo):
    raise ErrorValidacion(
        f"Archivo: {ruta}\n"
        f"Fila: {fila}\n"
        f"Campo: {campo}\n"
        f"Valor: {valor!r}\n"
        f"Motivo: {motivo}"
    )


def validar_fecha(valor, ruta, fila):

    patron = r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"

    if not re.fullmatch(patron, valor):
        error(
            ruta, fila, "InvoiceDate", valor,
            "Formato incorrecto. Se requiere AAAA-MM-DD HH:MM:SS."
        )

    try:
        return datetime.strptime(valor, FORMATO_FECHA)

    except ValueError:
        error(
            ruta, fila, "InvoiceDate", valor,
            "Fecha u hora imposible."
        )


def validar_cantidad(valor, ruta, fila):

    if not re.fullmatch(r"[0-9]+", valor):
        error(
            ruta, fila, "Quantity", valor,
            "La cantidad debe ser un numero entero positivo."
        )

    try:
        cantidad = int(valor)
    except ValueError:
        error(
            ruta, fila, "Quantity", valor,
            "Cantidad fuera del rango admitido."
        )

    if cantidad <= 0:
        error(
            ruta, fila, "Quantity", valor,
            "La cantidad debe ser mayor que cero."
        )

    return cantidad


def validar_precio(valor, ruta, fila):

    try:
        precio = float(valor)

    except ValueError:
        error(
            ruta, fila, "UnitPrice", valor,
            "El precio debe ser numerico."
        )

    if not math.isfinite(precio):
        error(
            ruta, fila, "UnitPrice", valor,
            "No se permiten valores infinitos ni NaN."
        )

    if precio <= 0:
        error(
            ruta, fila, "UnitPrice", valor,
            "El precio debe ser mayor que cero."
        )

    patron = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"

    if not re.fullmatch(patron, valor):
        error(
            ruta, fila, "UnitPrice", valor,
            "Formato numerico incorrecto."
        )

    return precio


def validar_archivo(ruta, lotes_permitidos):

    ruta = Path(ruta)

    if not ruta.is_file():
        error(
            ruta, "-", "-", "-",
            "El archivo no existe."
        )

    contador = 0
    lotes_detectados = set()

    try:
        with ruta.open(
            "r", encoding="utf-8-sig", newline=""
        ) as archivo:

            lector = csv.reader(archivo, strict=True)
            encabezados = next(lector, None)

            if encabezados is None:
                error(
                    ruta, 1, "Encabezados", "-",
                    "El archivo esta vacio."
                )

            if (
                len(encabezados) != len(COLUMNAS)
                or set(encabezados) != set(COLUMNAS)
            ):
                error(
                    ruta, 1, "Encabezados", encabezados,
                    "El archivo debe contener exactamente las siete columnas."
                )

            for valores in lector:

                fila = lector.line_num

                if len(valores) != len(COLUMNAS):
                    error(
                        ruta, fila, "Estructura", valores,
                        "La fila debe contener exactamente siete campos."
                    )

                registro = dict(zip(encabezados, valores))

                # Validar los campos de texto obligatorios.
                for campo in [
                    "InvoiceNo",
                    "StockCode",
                    "Description",
                ]:
                    if not registro[campo].strip():
                        error(
                            ruta, fila, campo,
                            registro[campo],
                            "El campo no puede estar vacio."
                        )

                # Validar fecha, cantidad y precio.
                fecha = validar_fecha(
                    registro["InvoiceDate"], ruta, fila
                )

                validar_cantidad(
                    registro["Quantity"], ruta, fila
                )

                validar_precio(
                    registro["UnitPrice"], ruta, fila
                )

                # Validar el tipo de lote.
                lote = registro["lote"]

                if lote not in lotes_permitidos or lote not in PERIODOS:
                    error(
                        ruta, fila, "lote", lote,
                        "Lote no permitido para este archivo."
                    )

                lotes_detectados.add(lote)

                if len(lotes_detectados) > 1:
                    error(
                        ruta, fila, "lote", lote,
                        "No se permite mezclar diferentes lotes."
                    )

                # Validar coherencia entre fecha y lote.
                periodo_esperado = PERIODOS[lote]

                if (
                    fecha.year,
                    fecha.month,
                ) != periodo_esperado:

                    error(
                        ruta,
                        fila,
                        "InvoiceDate",
                        registro["InvoiceDate"],
                        f"La fecha no corresponde al lote {lote}."
                    )

                contador += 1

    except (OSError, UnicodeError, csv.Error) as exc:

        error(
            ruta, "-", "Archivo", "-",
            f"No se pudo leer correctamente el CSV: {exc}"
        )

    if contador == 0:
        error(
            ruta, 2, "Registros", "-",
            "El archivo debe contener al menos una fila."
        )

    return {
        "archivo": ruta.name,
        "filas": contador,
        "lote": next(iter(lotes_detectados)),
        "valido": True,
    }


def verificar_integridad(
    ruta,
    hash_esperado=HASH_REFERENCIA,
):

    ruta = Path(ruta)

    hash_actual = hashlib.sha256(
        ruta.read_bytes()
    ).hexdigest()

    if hash_actual != hash_esperado:
        error(
            ruta, "-", "SHA-256", hash_actual,
            "El archivo de referencia ha sido modificado."
        )

    return hash_actual


def main():

    print("=" * 60)
    print("RETAIL SALES MONITOR")
    print("VALIDACION DE CALIDAD DE DATOS")
    print("=" * 60)

    try:

        referencia = validar_archivo(
            DATA_DIR / "referencia.csv",
            {"referencia"},
        )

        print(
            f"\n[OK] {referencia['archivo']}"
            f" | {referencia['filas']} filas"
            f" | Lote: {referencia['lote']}"
        )

        actual = validar_archivo(
            DATA_DIR / "actual.csv",
            {"control", "nuevo"},
        )

        print(
            f"[OK] {actual['archivo']}"
            f" | {actual['filas']} filas"
            f" | Lote: {actual['lote']}"
        )

        hash_actual = verificar_integridad(
            DATA_DIR / "referencia.csv"
        )

        print("\n[OK] Integridad de referencia verificada.")
        print(f"SHA-256: {hash_actual}")

        print("\n[OK] Todos los datos son validos.")
        print("[OK] Se permite continuar con la generacion del informe.")
        print("=" * 60)

        return 0

    except (ErrorValidacion, OSError) as exc:

        print(f"\n[ERROR] VALIDACION FALLIDA\n{exc}")
        print("\n[BLOQUEADO] No se permite publicar.")
        print("=" * 60)

        return 1


if __name__ == "__main__":
    sys.exit(main())
