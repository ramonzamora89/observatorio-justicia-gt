#!/bin/zsh
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
LOG=logs/estudio_$(date +%Y%m%d_%H%M%S).log
echo "=== inicio $(date) ===" | tee -a "$LOG"
for intento in 0 1 2 3; do
  [ "$intento" -gt 0 ] && { echo "--- espera 20 min, intento $intento ---" | tee -a "$LOG"; sleep 1200; }
  caffeinate -ims uv run obsgt cc-ptmp estudio-apelaciones --por-periodo 500 >> "$LOG" 2>&1
  codigo=$?
  echo "--- intento $intento codigo $codigo $(date) ---" | tee -a "$LOG"
  [ "$codigo" -ne 3 ] && break
done
echo "=== fin $(date) ===" | tee -a "$LOG"
