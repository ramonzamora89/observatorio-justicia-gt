# Tareas pendientes

Actualizado: 2026-08-30. En orden de prioridad.

---

## 1. Terminar la validación del clasificador · **bloquea publicar**

`data/manifests/cc_ptmp/validacion_resolutivo.csv` — 100 filas, unas pocas hechas.

Es lo único que impide publicar la matriz de confirmación/revocación. Hoy el
44,8% no tiene barra de error, y `PRD-1.md` §16 exige >95% de exactitud en el
resultado principal.

No hace falta terminar las 100: con 30 o 40 ya se distingue un 95% de un 80%.
Instrucciones en `auditorias/COMO_VALIDAR_EL_RESOLUTIVO.md`.

```bash
uv run obsgt cc-ptmp validar --puntuar
```

**Ojo con las 30 filas de «confirma con modificación».** Ahí el veredicto depende
de un criterio, no de leer bien, y mueve la tasa global de 44,8% a 28,1%.

---

## 2. Decidir el criterio amplio vs. estricto · **decisión, no trabajo**

Un fallo que dice «sin lugar el recurso… confirma la sentencia apelada, **con
modificación**» ¿altera la decisión revisada o la mantiene?

- Contándolo como altera: **44,8%**
- Sin contarlo: **28,1%**

Ambas series se publican hoy (`obsgt cc-ptmp tasas`), pero elegir una para el
titular es una decisión jurídica. Sale de la tarea 1.

---

## 3. Cerrar la ventana hasta 2026 · ~2 horas, $0

El censo cubre 1986-2026; el estudio se detiene en 2023. Faltan 2024, 2025 y
2026 —7,524 documentos publicados— justo donde la serie sube más.

```bash
uv run obsgt cc-ptmp muestra --desde 2024 --hasta 2026
uv run obsgt cc-ptmp atributos
```

---

## 4. Probar CIDEJ · única vía viva para primera instancia

El Centro de Información, Desarrollo y Estadística Judicial aparece como
operador de SICEJ y **no es CENADOJ**. Es un destinatario que nunca se ha
probado, y es la única puerta que queda para las fases 3 y 4 después de que el
portal del OJ resultara cerrado sin credencial de abogado y notario.

Trabajo de gestión, no de código.

---

## 5. Vinculación entre instancias (MVP-3) · sin empezar

`appeal_links` está vacía. La CC identifica al órgano inferior y la fecha de la
sentencia recurrida; con eso se puede empezar a reconstruir el ciclo procesal,
aunque solo hacia arriba.

`PIPELINE.md` §7 fija la prioridad de señales y prohíbe aceptar vínculos débiles.

---

## 6. Subuniverso del Ministerio Público · ~2,500 documentos, ~1,4 h

329 en la muestra actual. Es la línea base para preguntar si la Corte resuelve
distinto cuando quien pide amparo es la acusación.

---

## Cosas que NO hay que volver a intentar

- **Buscar en el endpoint de texto libre para contar.** No hace búsqueda de
  frase: «voto razonado disidente» devuelve 47,720 de 66,025 y «antejuicio»
  27,897. Cualquier conteo suyo es ruido.
- **La Gaceta Jurisprudencial para medir votos razonados.** Comprobado: son
  fichas por expediente, sin firmas ni votos. Cero menciones en 345 páginas.
- **El portal del OJ por vía automatizada.** Requiere credencial de abogado y
  notario, y hay desafío anti-bot. No se evade.
- **Publicar una serie temporal sin preguntar qué cambió en el documento.** Van
  tres veces que el patrón era de la fuente, no de la Corte.
