
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "datos"

print("=" * 50)
print("RETAIL SALES MONITOR - CAMBIO DE PERIODO")
print("=" * 50)

print("\n1. Octubre 2011")
print("2. Noviembre 2011")
print("3. Salir")

opcion = input("\nSelecciona un periodo: ")

if opcion == "1":
    origen = DATA_DIR / "control.csv"
    mes = "Octubre"

elif opcion == "2":
    origen = DATA_DIR / "nuevo.csv"
    mes = "Noviembre"

elif opcion == "3":
    sys.exit(0)

else:
    print("[ERROR] Opcion incorrecta.")
    sys.exit(1)

destino = DATA_DIR / "actual.csv"

# Sustituir el lote actual
shutil.copyfile(origen, destino)

print(f"\n[OK] Lote actualizado a {mes} 2011.")

# Generar nuevamente el dashboard y Evidently
resultado = subprocess.run(
    [sys.executable, "-m", "scripts.generar_informe"],
    cwd=BASE_DIR,
)

if resultado.returncode != 0:
    print("\n[ERROR] No se pudo generar el informe.")
    sys.exit(1)

print(f"\n[OK] Dashboard de {mes} generado correctamente.")
