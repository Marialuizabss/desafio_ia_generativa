# RF22 — Polaridade e painel

- Modo: **Real** — chamada ao modelo pela configuração principal
- Executado em: 2026-10-30T18:20:15-04:00
- Prompt: `prompts/desafio2/sentimento_v1.md` (versão `ee74f9f56985`) · esquema `1.0`
- Confiança: estimativa não calibrada. Não entra no percentual.
- Custo estimado: US$ 0.001741

## Painel

- Registros lidos: 12 · únicos: 12 · duplicados: —
- Denominador (classificadas): 12
- Rejeitadas (fora dos totais): 0
- Revisão: 5
- Mensagem: —

| Polaridade | Total | Fração | Percentual |
|---|---:|---|---:|
| positiva | 3 | 3/12 | 25.0% |
| negativa | 3 | 3/12 | 25.0% |
| neutra | 2 | 2/12 | 16.7% |
| indeterminada | 4 | 4/12 | 33.3% |

## Acurácia

- Polaridade: 10/12 (83.3%)
- Revisão: 11/12 (91.7%)

| Avaliação | Esperada → obtida | Revisão | Confiança |
|---|---|---|---:|
| AV01 | positiva → positiva (acerto) | não | 0.9 |
| AV02 | positiva → positiva (acerto) | não | 0.9 |
| AV03 | positiva → positiva (acerto) | não | 0.9 |
| AV04 | negativa → negativa (acerto) | não | 0.9 |
| AV05 | negativa → negativa (acerto) | não | 0.9 |
| AV06 | negativa → negativa (acerto) | sim | 0.9 |
| AV07 | neutra → neutra (acerto) | não | 0.8 |
| AV08 | neutra → neutra (acerto) | não | 0.8 |
| AV09 | neutra → indeterminada (erro) | sim | 0.6 |
| AV10 | negativa → indeterminada (erro) | sim | 0.7 |
| AV11 | indeterminada → indeterminada (acerto) | sim | 0.7 |
| AV12 | indeterminada → indeterminada (acerto) | sim | 0.5 |
