#!/bin/zsh
# Recoleccion de fichas de atributos, para correr de noche sin vigilancia.
#
# caffeinate -ims  : impide que el Mac se duerma (-i sin idle, -m disco despierto,
#                    -s mientras haya corriente). Sin esto la corrida muere.
# Reanudacion      : el comando salta los ids ya escritos, asi que relanzarlo
#                    continua donde iba.
# Si la fuente limita la tasa, el comando se detiene con codigo 3. Aqui se espera
# VEINTE MINUTOS antes de reintentar, y como maximo tres veces. Es retroceso
# cortes, no insistencia: si tras tres esperas sigue limitando, se para y punto.

cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
LOG=logs/atributos_$(date +%Y%m%d_%H%M%S).log
MAX_REINTENTOS=3
ESPERA=1200   # 20 minutos

echo "=== inicio $(date) ===" | tee -a "$LOG"
for intento in $(seq 0 $MAX_REINTENTOS); do
  if [ "$intento" -gt 0 ]; then
    echo "--- la fuente limito la tasa; esperando ${ESPERA}s antes del intento $intento ---" | tee -a "$LOG"
    sleep "$ESPERA"
  fi
  caffeinate -ims uv run obsgt cc-ptmp atributos >> "$LOG" 2>&1
  codigo=$?
  echo "--- intento $intento termino con codigo $codigo $(date) ---" | tee -a "$LOG"
  [ "$codigo" -ne 3 ] && break
done
echo "=== fin $(date) codigo=$codigo ===" | tee -a "$LOG"

python3 - "$LOG" <<'PY' | tee -a "$LOG"
import json, sys, collections, pathlib
p = pathlib.Path("data/processed/cc_ptmp/atributos.jsonl")
if not p.exists():
    print("RESUMEN: no se escribio nada"); raise SystemExit
filas = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
CLAVES = ("Sentido de la sentencia", "Sentido", "Fallo")
por = collections.defaultdict(lambda: [0, 0])
for f in filas:
    a = f.get("atributos") or {}
    tiene = any((a.get(k) or "").strip() for k in CLAVES)
    por[f["estrato_anio"]][0] += 1
    por[f["estrato_anio"]][1] += 1 if tiene else 0
hay = sum(v[1] for v in por.values())
print(f"\nRESUMEN: {len(filas):,} documentos recogidos, {hay:,} con sentido ({hay/len(filas):.0%})")
print("cobertura por anio:")
for a in sorted(por):
    n, c = por[a]
    print(f"  {a}  {c:>4}/{n:<4} {c/n:>5.0%}")
PY
