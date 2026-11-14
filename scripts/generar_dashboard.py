
import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from string import Template

import evidently

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"


AUTOR = "Juan Pablo Vargas"

MESES = {
    "control": "Octubre",
    "nuevo": "Noviembre",
}


def formato_numero(valor, decimales=2):

    texto = f"{valor:,.{decimales}f}"

    return texto.translate(
        str.maketrans(",.", ".,")
    )


def calcular_variacion(actual, referencia):

    if referencia == 0:
        return "No aplicable"

    variacion = (
        (actual - referencia) / referencia
    ) * 100

    if variacion == 0:
        return "Sin variacion"

    signo = "+" if variacion > 0 else ""

    return (
        f"{signo}{formato_numero(variacion)} %"
    )


def leer_drift(ruta_json):

    datos = json.loads(
        ruta_json.read_text(encoding="utf-8")
    )

    resultados = {}

    for metrica in datos["metrics"]:

        config = metrica["config"]

        if config["type"].endswith(":ValueDrift"):

            columna = config["column"]

            score = float(metrica["value"])

            umbral = float(config["threshold"])

            resultados[columna] = {
                "score": score,
                "umbral": umbral,
                "drift": score >= umbral,
            }

    esperadas = {"Quantity", "UnitPrice"}

    if set(resultados) != esperadas:

        raise ValueError(
            "El JSON no contiene las dos metricas esperadas."
        )

    return resultados


def crear_tabla_estadisticas(
    referencia, actual, columna
):

    indicadores = [
        ("Media", lambda s: s.mean()),
        ("Mediana", lambda s: s.median()),
        ("Primer cuartil", lambda s: s.quantile(0.25)),
        ("Tercer cuartil", lambda s: s.quantile(0.75)),
        ("Desv. estandar", lambda s: s.std()),
        ("Minimo", lambda s: s.min()),
        ("Maximo", lambda s: s.max()),
    ]

    filas = []

    for nombre, funcion in indicadores:

        valor_ref = funcion(referencia[columna])
        valor_actual = funcion(actual[columna])

        prefijo = "£" if columna == "UnitPrice" else ""

        ref = prefijo + formato_numero(valor_ref)
        act = prefijo + formato_numero(valor_actual)

        filas.append(
            f"""
            <tr>
                <td>{escape(nombre)}</td>
                <td class="number">{ref}</td>
                <td class="number">{act}</td>
            </tr>
            """
        )

    return "\n".join(filas)


def crear_tabla_productos(actual):

    productos = (
        actual.groupby("StockCode", sort=False)
        .agg(
            Description=("Description", "first"),
            Quantity=("Quantity", "sum"),
        )
        .sort_values("Quantity", ascending=False)
        .head(5)
    )

    filas = []

    for posicion, (codigo, producto) in enumerate(
        productos.iterrows(), start=1
    ):

        codigo_seguro = escape(str(codigo))

        descripcion = escape(
            str(producto["Description"])
        )

        unidades = formato_numero(
            producto["Quantity"], 0
        )

        filas.append(
            f"""
            <tr>
                <td>{posicion}</td>
                <td>{codigo_seguro}</td>
                <td>{descripcion}</td>
                <td class="number">{unidades}</td>
            </tr>
            """
        )

    return "\n".join(filas)


def obtener_metadatos_github():

    sha = os.getenv("GITHUB_SHA")

    repositorio = os.getenv("GITHUB_REPOSITORY")

    run_id = os.getenv("GITHUB_RUN_ID")

    if sha and repositorio:

        url = (
            f"https://github.com/{repositorio}"
            f"/commit/{sha}"
        )

        commit_html = (
            f'<a href="{escape(url)}" '
            f'title="{escape(sha)}">'
            f'{escape(sha[:7])}</a>'
        )

    else:

        commit_html = "Vista local - sin despliegue"

    if repositorio and run_id:

        url = (
            f"https://github.com/{repositorio}"
            f"/actions/runs/{run_id}"
        )

        ejecucion_html = (
            f'<a href="{escape(url)}">'
            "Ver ejecucion de Actions</a>"
        )

    else:

        ejecucion_html = "Ejecucion local"

    return commit_html, ejecucion_html


def generar_dashboard(referencia, actual, site_dir):

    site_dir = Path(site_dir)

    site_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    mes_actual = MESES[actual["lote"].iloc[0]]

    drift = leer_drift(
        site_dir / "drift_resultados.json"
    )

    cantidad = drift["Quantity"]

    precio = drift["UnitPrice"]

    umbral = cantidad["umbral"]

    if precio["umbral"] != umbral:

        raise ValueError(
            "Las metricas deben utilizar el mismo umbral."
        )

    total_drift = sum(
        resultado["drift"]
        for resultado in drift.values()
    )

    escala = max(
        umbral * 1.2,
        cantidad["score"] * 1.1,
        precio["score"] * 1.1,
    )

    mediana_cantidad = actual["Quantity"].median()

    mediana_precio = actual["UnitPrice"].median()

    if total_drift == 0:

        recomendacion = (
            "No se detectaron cambios que superen el "
            "umbral establecido. Se recomienda mantener "
            "el monitoreo mensual y revisar las variaciones "
            "descriptivas antes de modificar el inventario."
        )

        resumen_drift = "0 de 2 variables con drift"

    else:

        recomendacion = (
            "Se detectaron cambios en las distribuciones. "
            "El equipo de ventas debe revisar los productos "
            "y patrones de compra asociados a las variables "
            "afectadas. El lote es valido y puede publicarse."
        )

        resumen_drift = (
            f"{total_drift} de 2 variables con drift"
        )

    commit_html, ejecucion_html = (
        obtener_metadatos_github()
    )

    fecha_generacion = datetime.now(
        UTC
    ).strftime("%Y-%m-%d %H:%M:%S")

    valores = {

        "mes_actual": mes_actual,

        "mes_minusculas": mes_actual.lower(),

        "filas": formato_numero(len(actual), 0),

        "mediana_cantidad": formato_numero(
            mediana_cantidad, 1
        ),

        "mediana_precio": formato_numero(
            mediana_precio
        ),

        "variacion_cantidad": calcular_variacion(
            mediana_cantidad,
            referencia["Quantity"].median(),
        ),

        "variacion_precio": calcular_variacion(
            mediana_precio,
            referencia["UnitPrice"].median(),
        ),

        "version_evidently": evidently.__version__,

        "umbral": formato_numero(umbral, 2),

        "score_cantidad": formato_numero(
            cantidad["score"], 5
        ),

        "score_precio": formato_numero(
            precio["score"], 5
        ),

        "barra_cantidad": (
            f"{cantidad['score'] / escala * 100:.2f}"
        ),

        "barra_precio": (
            f"{precio['score'] / escala * 100:.2f}"
        ),

        "posicion_umbral": (
            f"{umbral / escala * 100:.2f}"
        ),

        "estado_cantidad": (
            "Drift detectado"
            if cantidad["drift"]
            else "Sin drift detectado"
        ),

        "estado_precio": (
            "Drift detectado"
            if precio["drift"]
            else "Sin drift detectado"
        ),

        "clase_cantidad": (
            "orange" if cantidad["drift"] else "green"
        ),

        "clase_precio": (
            "orange" if precio["drift"] else "green"
        ),

        "clase_barra_cantidad": (
            "fill-warning"
            if cantidad["drift"] else ""
        ),

        "clase_barra_precio": (
            "fill-warning"
            if precio["drift"] else ""
        ),

        "clase_general": (
            "orange" if total_drift else "green"
        ),

        "resumen_drift": resumen_drift,

        "recomendacion": escape(recomendacion),

        "tabla_cantidad": crear_tabla_estadisticas(
            referencia,
            actual,
            "Quantity",
        ),

        "tabla_precio": crear_tabla_estadisticas(
            referencia,
            actual,
            "UnitPrice",
        ),

        "tabla_productos": crear_tabla_productos(
            actual
        ),

        "autor": escape(AUTOR),

        "fecha_generacion": fecha_generacion,

        "commit_html": commit_html,

        "ejecucion_html": ejecucion_html,
    }

    plantilla = Template(
        TEMPLATE_PATH.read_text(encoding="utf-8")
    )

    html = plantilla.substitute(valores)

    ruta_salida = site_dir / "index.html"

    ruta_salida.write_text(
        html,
        encoding="utf-8",
    )

    print("\nRESULTADO DEL DASHBOARD")
    print("-" * 60)

    print(f"Periodo: {mes_actual} 2011")

    print(f"Registros: {len(actual)}")

    print(
        f"Mediana Quantity: {mediana_cantidad}"
    )

    print(
        f"Mediana UnitPrice: {mediana_precio}"
    )

    print(f"Variables con drift: {total_drift}/2")

    print(f"[OK] Dashboard generado: {ruta_salida}")
