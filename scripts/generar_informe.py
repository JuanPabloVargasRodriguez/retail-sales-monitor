
from pathlib import Path

import evidently
import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset

from scripts.generar_dashboard import generar_dashboard
from scripts.validar_datos import main as validar_datos

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "datos"
SITE_DIR = BASE_DIR / "site"

VARIABLES = ["Quantity", "UnitPrice"]

METODO = "wasserstein"
UMBRAL = 0.1

MESES = {
    "referencia": "Septiembre",
    "control": "Octubre",
    "nuevo": "Noviembre",
}


def cargar_datos():

    referencia = pd.read_csv(
        DATA_DIR / "referencia.csv"
    )

    actual = pd.read_csv(
        DATA_DIR / "actual.csv"
    )

    return referencia, actual


def mostrar_estadisticas(referencia, actual):

    for variable in VARIABLES:

        print(f"\nVARIABLE: {variable}")
        print("-" * 60)

        resumen = pd.DataFrame({
            "Referencia": referencia[variable].describe(),
            "Actual": actual[variable].describe(),
        })

        print(resumen.round(4).to_string())


def generar_reporte(referencia, actual):

    SITE_DIR.mkdir(parents=True, exist_ok=True)

    definicion = DataDefinition(
        numerical_columns=VARIABLES,
    )

    dataset_referencia = Dataset.from_pandas(
        referencia[VARIABLES].copy(),
        data_definition=definicion,
    )

    dataset_actual = Dataset.from_pandas(
        actual[VARIABLES].copy(),
        data_definition=definicion,
    )

    reporte = Report(
        [
            DataDriftPreset(
                columns=VARIABLES,
                method=METODO,
                threshold=UMBRAL,
                drift_share=0.5,
                include_tests=False,
            )
        ],
        include_tests=False,
    )

    resultado = reporte.run(
        current_data=dataset_actual,
        reference_data=dataset_referencia,
    )

    # Informe visual de Evidently.
    ruta_html = SITE_DIR / "informe_evidently.html"

    resultado.save_html(str(ruta_html))

    # Resultados estructurados para el dashboard.
    ruta_json = SITE_DIR / "drift_resultados.json"

    ruta_json.write_text(
        resultado.json(),
        encoding="utf-8",
    )

    print("\nRESULTADOS DE EVIDENTLY")
    print("-" * 60)

    print(resultado.json())

    print(f"\n[OK] Informe HTML: {ruta_html}")
    print(f"[OK] Resultados JSON: {ruta_json}")

    return resultado


def main():

    # Impedir la generacion con datos invalidos.
    if validar_datos() != 0:
        return 1

    print("\n" + "=" * 60)
    print("RETAIL SALES MONITOR")
    print("MONITOREO ESTADISTICO CON EVIDENTLY")
    print("=" * 60)

    referencia, actual = cargar_datos()

    mes_actual = MESES[actual["lote"].iloc[0]]

    print(f"\nVersion de Evidently: {evidently.__version__}")
    print("Referencia: Septiembre 2011")
    print(f"Lote actual: {mes_actual} 2011")

    print(f"Filas de referencia: {len(referencia)}")
    print(f"Filas actuales: {len(actual)}")

    print(f"Metodo: {METODO}")
    print(f"Umbral: {UMBRAL}")

    mostrar_estadisticas(referencia, actual)

    generar_reporte(referencia, actual)
    generar_dashboard(
    referencia,
    actual,
    SITE_DIR,
    )

    print("\n[OK] Monitoreo completado correctamente.")
    print("[OK] El drift no bloquea la publicacion.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
