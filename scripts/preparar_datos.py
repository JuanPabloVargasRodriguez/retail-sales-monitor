
import csv
import hashlib
import shutil
from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "datos"
ORIGINAL = DATA_DIR / "original" / "ventas_regalos_2011.csv"

COLUMNAS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "InvoiceDate",
    "Quantity",
    "UnitPrice",
    "lote",
]

LOTES = {
    "referencia": "referencia.csv",
    "control": "control.csv",
    "nuevo": "nuevo.csv",
}

FILAS_ESPERADAS = 12000


def calcular_hash(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def preparar_datos():

    print("=" * 60)
    print("RETAIL SALES MONITOR")
    print("PREPARACION DE LOTES DE VENTAS")
    print("=" * 60)

    if not ORIGINAL.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo: {ORIGINAL}"
        )

    hash_original = calcular_hash(ORIGINAL)

    grupos = {lote: [] for lote in LOTES}

    # Leer el archivo original sin modificarlo
    with ORIGINAL.open(
        "r", encoding="utf-8-sig", newline=""
    ) as archivo:

        lector = csv.DictReader(archivo)

        if lector.fieldnames != COLUMNAS:
            raise ValueError("Las columnas no son las esperadas.")

        for fila in lector:
            if fila["lote"] not in grupos:
                raise ValueError(
                    f"Lote desconocido: {fila['lote']}"
                )

            grupos[fila["lote"]].append(fila)

    # Comprobar los tamaños antes de generar archivos
    for lote, filas in grupos.items():
        if len(filas) != FILAS_ESPERADAS:
            raise ValueError(
                f"{lote}: se esperaban {FILAS_ESPERADAS} "
                f"filas, pero se encontraron {len(filas)}."
            )

    print("\nArchivo original localizado correctamente.")
    print(f"Total de registros: {sum(map(len, grupos.values()))}")

    print("\nDISTRIBUCION DE LOTES")
    print("-" * 60)

    # Generar los tres lotes
    for lote, nombre_archivo in LOTES.items():

        destino = DATA_DIR / nombre_archivo

        with destino.open(
            "w", encoding="utf-8", newline=""
        ) as archivo:

            escritor = csv.DictWriter(
                archivo,
                fieldnames=COLUMNAS,
                lineterminator="\n",
            )

            escritor.writeheader()
            escritor.writerows(grupos[lote])

        print(
            f"[OK] {nombre_archivo:<18}"
            f"{len(grupos[lote]):>6} filas"
        )

    # Crear actual.csv para la primera publicacion
    control = DATA_DIR / "control.csv"
    actual = DATA_DIR / "actual.csv"

    if not actual.exists():
        shutil.copyfile(control, actual)
        print("\n[OK] actual.csv creado a partir de control.csv")
    else:
        print("\n[INFO] actual.csv ya existe. No se ha reemplazado.")

    # Verificar la integridad del archivo original
    if calcular_hash(ORIGINAL) != hash_original:
        raise RuntimeError("El archivo original fue modificado.")

    print("\nINTEGRIDAD DE LOS DATOS")
    print("-" * 60)

    print("[OK] El archivo original permanece intacto.")
    print(f"SHA-256 original: {hash_original}")

    hash_referencia = calcular_hash(DATA_DIR / "referencia.csv")
    print(f"SHA-256 referencia: {hash_referencia}")

    print("\n[OK] Preparacion completada correctamente.")
    print("=" * 60)


if __name__ == "__main__":
    preparar_datos()
