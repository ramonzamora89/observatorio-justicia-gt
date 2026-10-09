# Ficha: lista de magistrados de la CC por magistratura

**Archivo:** `sources/cc/magistrados.csv` · **Preparada:** 2026-10-09

## Fuente

Wikipedia, «Anexo:Composición de la Corte de Constitucionalidad de Guatemala»,
revisión **175473409** (2026-09-22T02:46:47Z), bajada en wikitext crudo
(`action=raw`) el 2026-10-09. Copia local (fuera de git):
`data/raw/wikipedia/2026-10-09_composicion_cc.wikitext`, SHA-256
`4ab5a4223cdac11d49f064acf2f21d45ed06047e8e33bd55f286890633a8596c`.

Es **fuente secundaria**. Sirve de lista inicial; **la firma de la sentencia
manda sobre ella**. Uso: `observatorio_gt.integracion`.

## Columnas

`magistratura` (I a IX), `nombre` (como lo escribe Wikipedia, sin
«Licenciado»), `cargo` (titular/suplente), `desde`/`hasta` (años del cargo),
`designado_por`, `fuente`.

## Lo que se encontró al cotejar con las firmas (muestra de 8.568)

**Permanencias que Wikipedia no lista**, agregadas con `fuente=firmas`:

- **José Francisco De Mata Vela** sigue firmando en la VIII hasta el
  2022-07-13; Pérez Aguilera aparece desde el 2022-08-02.
- **Manuel Duarte Barrera** firma en 2015, en el puesto que Wikipedia da como
  vacante. Designante no verificado.

**Grafías distintas** entre Wikipedia y la firma: van en
`integracion.VARIANTES` y **no se corrigen en la lista**. Entre ellas:
«Quedada Toruño» (firma: Quezada), «Concha Mazariegos» (firma: Conchita),
«Melgar Rojas de Aguilar» (firma: Melgar de Aguilar).

**Prórrogas.** En 2021, integrantes de la VII firmaron meses dentro de la
VIII. El cotejo admite un año después del fin del cargo.

## Resultado del cotejo

97,4% de las resoluciones de la muestra con 5 o 7 magistrados reconocidos (la
integración del pleno). El resto: erratas en la firma («PÉREZ AGUILEA»,
«GUTIERRES»), firmas ausentes o fechas de resolución equivocadas.

Las fechas del portal pueden estar mal: una sentencia fechada en octubre de
2021 la firma la integración de la VII. **Una integración que no corresponde a
la fecha es una alerta sobre la fecha.**
