# Upstream: consolidação episódica vaza `<think>` cru do LLM

- **Data:** 09/08/2026 · **Sessão:** 48 (hygiene) · **Repo:** `mnemosyne-oss/mnemosyne` (upstream)
- **Severidade:** baixa (cosmética → média com gate 0.0) · **Tipo:** bug de formatação na consolidação
- **Status:** aberta — issue upstream pendente · **Rastreado em:** `docs/DECISIONS.md` (D14)

---

## Síntoma

Memórias em `episodic_memory` cujo `content` começa com um bloco `<think>` cru — o
raciocínio interno do LLM usado na consolidação do sono foi gravado **dentro do conteúdo**
da memória, em vez de apenas o resumo final.

## Evidência (produção, mnemosyne 3.16.0 @ `c4344f2d`)

11 ocorrências em `episodic_memory` (varredura `hygiene_audit` + consulta direta ao SQLite):

| ID | Timestamp | Conteúdo (início) |
|---|---|---|
| `b2308842…` | 2026-07-17 | `<think> First, I need to summarize the memories into 1-3 concise sentences…` |
| `74622ea2…` | 2026-07-17 | `<think> The user wants a summary of the provided memories… I think I have enough…` |
| `6c361b12…` | 2026-07-18 | `<think> First, I need to summarize the memories…` |
| `33dd987e…` | 2026-07-20 | `<think> First, I need to summarize the memories…` |
| `286520c6…` | 2026-07-22 | `<think> …` (contém resumo real embutido) |
| `b35bf77e…` | 2026-07-22 | `<think> Okay, the user wants me to summarize…` (contém resumo real embutido) |
| `9e8dca84…` | 2026-07-24 | `<think> First, I need to summarize…` (contém resumo real embutido) |
| `04d30952…` | 2026-07-29 | `<think> First, I need to summarize…` |
| `789d11ae…` | 2026-07-31 | `<think> … NB02 NB02 NB02 …` (repetição anômala) |
| `9667ecc4…` | 2026-08-03 | `<think> First, I need to summarize…` (contém resumo real embutido) |
| `b955d642…` | 2026-08-07 | `<think> First, I need to summarize…` |

- **8 deletadas** (lixo puro — raciocínio sem resumo útil).
- **4 preservadas** (`286520c6…`, `9667ecc4…`, `9e8dca84…`, `b35bf77e…`) por conterem o
  resumo real após o bloco `<think>` — não deletar a informação.

## Por que importa

- Polui o recall: com `MNEMOSYNE_LEXICAL_GATE_MIN=0.0` (recall-first), memórias `<think>`
  ressurgem no topo (overlap de tokens com o prompt de sumarização).
- Consome contexto: o `<think>` pode ter 1–7 KB por memória, repetido em recalls.

## Causa provável

No fluxo `sleep()` → `consolidate_to_episodic(summary=…)`, o `summary` passado ao INSERT
vem do retorno do LLM **sem strip do bloco `<think>…</think>`** (ou o provider retorna
`reasoning_content` + `content` e o código concatena o reasoning). O padrão dos conteúdos
("First, I need to summarize the memories into 1-3 concise sentences…") confirma que é o
raciocínio do prompt de consolidação vazando para o armazenamento.

## Draft de issue (para o upstream)

> **Title:** `sleep_consolidation` stores raw LLM `<think>` blocks in `episodic_memory`
>
> **Body:**
> When the nightly `sleep()` consolidation runs, the LLM's internal reasoning block
> (`<think>…</think>`) is stored verbatim as the `content` of `episodic_memory` rows
> instead of just the final summary. Found 11 rows across 3 weeks in production
> (mnemosyne 3.16.0); some contain the real summary after the think block, others are
> pure reasoning (e.g. "I think I have enough…"). Impact: pollutes recall under
> `MNEMOSYNE_LEXICAL_GATE_MIN=0.0` and wastes context (~1–7 KB per row).
>
> **Suggested fix:** in the `sleep()`/`consolidate_to_episodic` path, strip the
> `<think>…</think>` block (regex or `reasoning_content` handling) from the summary
> before the INSERT — or truncate at the first `</think>`.
>
> **Repro:** run `sleep()` with any LLM backend that emits reasoning; inspect
> `episodic_memory.content` for a leading `<think>`.

## Tratamento local (já feito)

- Hygiene sessão 48: 8 linhas deletadas, 4 preservadas (resumo real).
- Nenhuma edição em `site-packages` (política do projeto, D12).
- Fix real = upstream (strip do `<think>` na consolidação).
