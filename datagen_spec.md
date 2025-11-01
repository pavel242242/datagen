## Datagen Spec (MVP) — Universal, Schema‑First Dataset Generator

### Purpose
- Universal, realistic synthetic data from any domain (health, sports, ecommerce, weather, airports, …).
- Simplicity and explainability: small JSON DSL defines everything; deterministic, vectorized runtime interprets it.
- LLM is optional: converts natural language to strict JSON DSL; runtime stays fixed and safe.

---

### Core Principles
- Schema defines everything (no domain code in runtime)
- Small, composable primitives → realism via composition (distributions, time patterns, effects)
- Deterministic seeds for reproducibility
- Vectorized where possible; batched where needed
- Strict validation and guardrails; concise defaults

---

### Design Principles (Reuse vs Build)

Reuse existing, proven libraries for heavy lifting:
- Schema & validation: Pydantic (models), jsonschema (runtime validation)
- Data & vectorization: pandas, numpy (np.random.Generator)
- I/O: pyarrow (Parquet)
- CLI: Click or Typer
- Semantics: Faker (names/addresses with locale)
- Stats: numpy/scipy (basics), statsmodels (optional GLM)
- Regex/expressions: re, numexpr (whitelisted ops)
- Caching/logging: filesystem, diskcache (optional), logging

Build only thin, universal layers:
- DSL definition (Pydantic + JSON Schema) and strict validator
- Function registry of primitives/modifiers/validators (stable ids)
- Deterministic seed derivation across node/column/parent/row scopes
- DAG builder (parents + refs → toposort levels)
- Executor (interprets DSL → registry calls; vectorized/batched; clamp→cast pipeline)
- Validator/Reporter (PK/FK/range/enum/pattern/inequality + behavioral/targets/composite effects; quality score; JSON report)
- LLM adapter (optional): constrained JSON-only prompts, schema validation, auto-repair loop (no runtime codegen)

Intentional MVP simplifications:
- Multiplicative effects by default (additive only if specified)
- One primary parent per fact
- Limited distributions (uniform, normal, lognormal, poisson) with mandatory clamps
- Seasonality limited to hour/dow/month weights
- Outliers: spike/drop modes with simple rate + magnitude_dist
- Expressions via numexpr with strict whitelist (no Python exec)
- JSON report first; HTML later

---

### Architecture Overview

Components (thin, explainable):
- CLI: `create` (optional NL→DSL), `generate`, `validate`, `--dry-run-sample`.
- LLM Adapter (optional): constrained prompting; JSON Schema validation; auto‑repair loop.
- Schema Layer: Pydantic models + JSON Schema; defaulting; strict rejection of unknown fields.
- DAG Builder: infers dependencies from `parents` and cross‑table references; topological sort by levels.
- Seed Manager: deterministic derivation per node/column/parent/row; provides `np.random.Generator`.
- Generation Engine: interprets DSL using a function registry (primitives + modifiers); vectorized where possible; batched otherwise.
- Validator: structural, value, behavioral checks; target evaluation; quality scoring; JSON report.
- Output Manager: Parquet writer + `.metadata.json` (schema hash, seeds, runtime); future formats optional.

Data flow:
`Natural Language (optional)` → LLM Adapter → `DSL JSON` → Schema Layer → DAG Builder → Generation Engine → Output → Validator → Report

---

### Tooling & Integrations

Current stack (MVP):
- Pydantic v2 (DSL models) + jsonschema (validation)
- pandas + numpy (vectorization, RNG)
- pyarrow/Parquet (I/O)
- Click/Typer (CLI)
- Faker (semantics, with locale)
- logging (runtime logs)

Recommended substitutions/adapters:
- Faker/Mimesis adapter: support both; default to Faker, allow `--semantics-provider mimesis`
- NetworkX for DAG: use `nx.topological_generations()` instead of custom toposort
- Expressions: numexpr for vectorized math; simpleeval/asteval for safe row‑wise expressions (no builtins)
- Optional validation at scale: Pandera (dataframe schemas), DuckDB (SQL checks on Parquet)
- Optional performance: Polars as an alternative DataFrame backend (v1.1)
- Optional reporting: Great Expectations for rich HTML reports (v1.1+ if demanded)

Locale mapping (semantics):
- Use `pycountry` + `babel` to resolve ISO country → locale (e.g., `US→en_US`), with a curated fallback table.

Why these choices:
- Reuse mature libraries for graphs, vectorization, I/O, and validation to minimize custom code.
- Keep our unique logic focused on the universal DSL, deterministic execution, relationships/fanout, and realism layering.

Roadmap of integrations:
- Now (MVP): NetworkX, Faker/Mimesis adapter, simpleeval for expressions, Rich for CLI output
- MVP+ (v1.1): Pandera for runtime dataframe validation, DuckDB for large validation, Polars backend option, JSON→HTML report
- v2: Great Expectations integration, advanced stats (GLM) only if requested, hypothesis‑style constraint solving (research)

---

### JSON DSL (v1)

Required top‑level:
- `version: string`  e.g., "1.0"
- `metadata: { name: string }`
- `timeframe: { start: ISO8601, end: ISO8601, freq: "H|D|M|..." }`
- `nodes: Node[]`
- `constraints: Constraints`

Optional top‑level:
- `targets: Targets`  // small realism checks
- `dag: string[][]`   // generation levels; inferred if omitted

Node:
- `id: string`
- `kind: "entity" | "fact"`
- `pk: string`
- `parents?: string[]`  // MVP: at most one primary parent for facts
- `fanout?: Fanout`     // facts only
- `columns: Column[]`

Column:
- `name: string`
- `type: "int"|"float"|"string"|"bool"|"datetime"|"date"`
- `nullable: boolean`
- `generator: GeneratorSpec` // exactly one
- `modifiers?: ModifierSpec[]` // applied in order
- `constraints?: { pattern?: string, enum?: string[], enum_ref?: string }`

Fanout (facts):
- `{ distribution: "poisson"|"uniform", lambda?: number, min?: number, max?: number, clamp?: [min,max] }`

GeneratorSpec (allowed primitives):
- `sequence: { start?: int, step?: int }`
- `choice: {
      choices?: any[],
      choices_ref?: "table.column",
      weights?: number[],
      weights_kind?: "uniform"|"zipf@alpha"|"head_tail@{head_share,tail_alpha}"
  }`
- `distribution: { type: "normal"|"lognormal"|"uniform"|"poisson", params: object, clamp?: [min,max] }`
- `datetime_series: { within: "timeframe" | { start: ISO8601, end: ISO8601 }, freq: "H|D|M|...", pattern?: { dimension: "hour"|"dow"|"month", weights: number[] } }`
- `faker: { method: string, locale_from?: string | ColumnRef }` // e.g., name, address; locale derived from a column like country
- `lookup: { from: "table.column", on?: { this_key: other_key } }` // FK/backfills
- `expression: { code: string }` // tiny safe evaluator; arithmetic over columns only
- `enum_list: { values: any[] }` // for vocab nodes

ModifierSpec (generic effects):
- `{ transform: "multiply"|"add"|"clamp"|"jitter"|"map_values"|"seasonality"|"time_jitter"|"effect"|"outliers",
     args: object }`

Constraints (MVP):
- `unique: string[]`            // ["table.pk", ...]
- `foreign_keys: { from: string, to: string }[]`
- `ranges: { attr: string, min?: number, max?: number }[]`
- `inequalities?: { left: string, op: "<"|"<="|">"|">="|"==", right: string }[]`
- `pattern?: { attr: string, regex: string }[]`
- `enum?: { attr: string, values?: any[], enum_ref?: string }[]`

Targets (MVP examples):
- `weekend_share: { table: string, timestamp: string, min: number, max: number }`
- `mean_in_range: { table: string, column: string, min: number, max: number }`
- `composite_effect: { table: string, metric: string, influences: [
      { kind: "seasonality", dimension: "hour|dow|month", weights: number[] },
      { kind: "effect", table: string, on: object, field: "multiplier", default: 1.0 },
      { kind: "outliers", rate: number, mode: "spike|drop" }
  ], tolerance: { mae: number, mape: number } }`

Notes:
- All weights are normalized internally.
- Unknown keys are rejected by schema validation.

---

### Realism via Composition (Universal)

Seasonality:
- Represent as `datetime_series.pattern` with `dimension: hour|dow|month` and weights (mean≈1). Multiple patterns multiply.
- Optional modifier: `{ transform: "seasonality", args: { dimension, weights } }` to scale numeric columns by time.

Shocks / Effects (events that change levels):
- Model as normal tables (nodes) with windows `valid_from/valid_to` and keys (e.g., region/category).
- Apply with modifier `effect`:
  - `args: { effect_table, on: { local_key: effect_key }, window: { start_col, end_col }, map: { field: "multiplier"|"delta", op: "mul"|"add", default: 1.0 } }`

Outliers / Anomalies (rare):
- Modifier `outliers`:
  - `args: { rate: number, mode: "spike"|"drop"|"burst", magnitude_dist: { type, params }, allow_exceed?: boolean }`

Noise / Jitter:
- `jitter` for numeric, `time_jitter` for timestamps.

Enums / Vocabularies:
- Use `choice` with `choices` (inline), `choices_ref` (reuse from vocab node), or external URI (future).
- Prefer weighting strategies for long tails: `weights_kind: "zipf@alpha"` or explicit head/tail.
- Validate with `constraints.enum`/`enum_ref`.

Names / Addresses at Scale:
- Generate geo columns first (`country` → `state` → `city`) via `choice`/`lookup`.
- Use `faker` with `locale_from: "country"` (runtime maps `US→en_US`, `DE→de_DE`, …) for `name`, `address`, `postcode` (with optional `pattern` per country).

---

### Deterministic Seeds
- `master_seed` implicit default (42) or explicit via CLI; derived seeds ensure reproducibility.
- Derivation (concept): `seed = sha256(master_seed, node_id, column_name?, partition?, parent_pk?, row_index?) → int32`.
- All stochastic functions accept an RNG derived from the seed.

---

### Execution Engine (Interpreter)
1) Parse & Validate DSL (Pydantic + JSON Schema). Reject unknown keys; auto‑fill safe defaults.
2) Build DAG (toposort): infer from `parents` and `lookup`/`choices_ref` references if `dag` omitted.
3) Generate per DAG level:
   - Entities: vectorized column generation (generator → modifiers pipeline) with explicit dtype casts.
   - Facts: iterate parent rows; sample `fanout` per parent; form FK rows; generate remaining columns; apply modifiers/effects/outliers; clamp.
4) Validate (MVP): PK uniqueness, FK integrity, ranges; optional inequalities/pattern/enum.
5) Check Targets: simple aggregates (e.g., weekend share).
6) Output: Parquet (default) + `.metadata.json` (schema hash, seeds, runtime info).

Performance:
- Vectorize `sequence`, `choice`, `distribution`; batch fanout; chunk Faker calls.
- Memory safety via chunked processing when needed.

---

### End‑to‑End Workflow

1) Authoring (two paths):
   - Direct: write `schema.json` in DSL by hand or from template.
   - NL‑assisted (optional): `datagen create --description "..."` → LLM emits DSL → validate → auto‑repair if needed → save.
2) Preflight: `datagen generate --dry-run-sample 1000` compiles the plan, runs sample generation, performs quick validation; prints issues early.
3) Generation: run full DAG, writing per‑node Parquet; seeds ensure reproducibility; chunked processing for scale.
4) Validation: `datagen validate` loads outputs and schema; runs structural/value/behavioral checks; computes quality score; writes `validation_report.json`.
5) Iterate (optional): if score < threshold or violations present, adjust DSL (manually or via LLM refine) and rerun.

Retry policy (LLM path):
- On DSL validation error: show concise errors → re‑prompt to re‑emit minimal corrected JSON.
- On preflight generation error: suggest auto‑simplifications (reduce distributions, remove unknown modifiers, add clamps) and re‑run once.

---

### Logical Execution Details

- Seeding:
  - `seed_node = sha256(master_seed, node_id)`
  - `seed_col = sha256(seed_node, column_name)`
  - Facts: `seed_parent = sha256(seed_node, parent_pk)` for fanout; per child row derive `seed_row`.
- Entities:
  - For each column: build values via `generator(col_spec, rng(seed_col))` → fold modifiers in order.
  - Enforce PK uniqueness: `sequence` default for pk; or validate uniqueness post‑gen.
- Facts:
  - For each parent row: `k = fanout_per_parent(...)` → append `k` child rows with FK.
  - Generate other columns with per‑column seeds; apply modifiers and effects joins.
- Lookups/Refs:
  - `choices_ref` and `lookup` materialize referenced columns into memory‑efficient dictionaries; join via pandas merge.
- Modifiers ordering:
  - Always: `base generator` → `[modifiers...]` → `clamp` → `cast`.
- Performance:
  - Entities fully vectorized; facts batched by parent ranges; Faker executed in chunks with per‑chunk seeds.

---

### Extensibility & Error Handling

Extensibility:
- New primitives/modifiers added by extending the function registry (id + signature); DSL gains the id; validator updated.
- Versioned ids (e.g., `distribution@2`) allow safe evolution.
- Additional outputs (CSV/JSON/SQL) via Output Manager without changing DSL.

Error handling:
- DSL validation: fail fast with precise field paths; suggest auto‑fixes (add clamp, set dtype, remove unknown key).
- Runtime: surface first error with node/column context; record to report; stop or continue based on `--strict`.
- Validator: classify as `error|warning`; exit code 0 only when hard constraints pass and quality score ≥ threshold.

---

### Function Vocabulary (Internal Registry)
Base generators:
- `sequence(start, step, size)`
- `choice(choices|choices_ref, weights, size, rng)`
- `distribution(kind, params, size, rng, clamp)`
- `datetime_series(freq, start, end, size, pattern, rng)`
- `faker(method, locale)`
- `lookup(from, on)`
- `fanout_per_parent(kind, params, clamp, rng)`

Modifiers:
- `multiply`, `add`, `clamp`, `jitter`, `map_values`, `seasonality_multiplier`, `time_jitter`, `apply_effect`, `inject_outliers`, `safe_expr`

Validation:
- `validate_unique`, `validate_fk`, `validate_range`, `validate_inequality`, `validate_enum`, `validate_pattern`

Note: The DSL references only these ids; runtime maps ids → functions. Version ids may be introduced later (e.g., `distribution@1`).

---

### LLM Integration (Optional)
Goal: natural language → strict DSL that uses only allowed primitives.

Flow:
- Constrained prompt: "Output valid JSON only; conform to this JSON Schema; use only allowed generator ids."
- Validate; if invalid, re‑prompt with concise validator errors (auto‑repair).
- Fill defaults (seeds, clamps, dtypes) and confirm ambiguities with ≤2 questions.
- No model‑written runtime code required.

---

### LLM Responsibilities (MVP)
- Inputs: free‑form description, optional examples, optional target scale/timeframe.
- Outputs: a strict DSL plan that:
  - Defines nodes (entities/facts), columns, generators, modifiers, constraints, optional targets.
  - Normalizes enums (dedupe, canonical names), proposes weights (uniform/zipf/head‑tail).
  - Chooses simple, explainable distributions (uniform/lognormal/poisson) with safe clamps.
  - Encodes seasonality via `datetime_series.pattern` (hour/dow/month) when described.
  - Suggests minimal `targets` (e.g., weekend_share, mean_in_range) when feasible.
- Clarification policy: ask ≤2 yes/no or single‑choice questions only when essential (e.g., timeframe missing).
- Auto‑repair loop: when DSL validation fails, re‑emit a compact corrected JSON (no prose) addressing only the errors provided.
- Out‑of‑scope (MVP): writing runtime code, introducing functions not in registry, performing I/O.

---

### CLI (MVP)
- `datagen create --description "..." > schema.json`  // optional NL→DSL
- `datagen generate schema.json --seed 42`             // produce Parquet + metadata
- `datagen validate schema.json --data ./output`       // constraints + targets + report
- `--dry-run-sample 1000`                              // preflight small run

---

### Dataset Validation & Reporting (MVP)
What is validated after generation:
- Structural:
  - PK uniqueness for all `constraints.unique`
  - FK integrity for all `constraints.foreign_keys`
  - Nullability: no nulls in non‑nullable columns
  - Dtypes: columns conform to declared `type`
- Value rules:
  - Ranges (min/max) for all `constraints.ranges`
  - Inequalities for all `constraints.inequalities` (e.g., start < end)
  - Pattern/regex for all `constraints.pattern`
  - Enum membership for `constraints.enum` / `enum_ref`
- Behavioral checks (if configured):
  - Seasonality: compare observed distribution by `hour|dow|month` to configured weights (tolerance band; absolute deviation or chi‑square)
  - Targets: e.g., `weekend_share` within [min, max]; `mean_in_range` bounds
- Outliers (if modifier configured):
  - Observed outlier share vs requested `rate` ± tolerance; list top‑N examples

Report outputs:
- Machine‑readable JSON (and console summary):
  - `summary`: totals, quality_score (0–100), passed/failed counts
  - `constraints`: per‑rule results with violations and up to N examples
  - `behaviors`: seasonality metrics, deviations, target checks, composite effects
  - `tables`: per‑table row/column counts, missingness, inferred dtypes
  - `recommendations`: compact list of improvements when applicable

Quality score (default weighting):
- `score = 0.45*constraint_pass_rate + 0.25*behavior_score + 0.20*stat_validity + 0.10*relationship_integrity` (scaled 0–100)
  - Constraint pass rate = proportion of constraint checks passing
  - Behavior score = 1 − normalized deviation from weights/targets
  - Statistical validity = simple distribution sanity (e.g., nonzero variance, bounded skew)
  - Relationship integrity = FK success rate

Exit codes:
- `0` if all hard constraints (PK/FK) pass and quality_score ≥ threshold (default 80)
- `1` otherwise (details in JSON report)

Files:
- `./output/validation_report.json`
- Optional future: `validation_report.html`

---

### Composite Effects Validation (Weekday × Weather × Spike)

Goal: verify that combined influences yield the expected multiplicative (or additive) effect on a target metric (e.g., `amount`, `demand`).

Assumption (default): multiplicative model on the metric scale; additive on log‑metric.
- Expected: `metric ≈ base × seasonality(dow|hour|month) × effect(weather/promos) × spike_factor (rare)`

Configuration:
- Provide via `targets.composite_effect` with a list of influences. Seasonality weights come from DSL (`datetime_series.pattern` or a `seasonality` modifier). Effect multipliers come from an `effect` modifier joined from an effect table. Outlier rate/mode comes from `outliers` modifier.

Procedure:
1) Binning & stratification:
   - Build strata over the Cartesian product of declared influences (e.g., `dow × weather_condition`), with optional spike flag when applicable.
   - Drop sparse strata below a minimum count threshold; fall back to marginal checks.
2) Observed lift:
   - For each stratum `s`, compute `obs_mean = mean(metric_s)` (or median for robustness), and `lift_obs = obs_mean / mean(metric_baseline)` where baseline uses neutral conditions (e.g., midweek + clear + no spike) or overall mean if neutral not specified.
3) Expected lift:
   - Multiply declared multipliers for that stratum: `lift_exp = seasonality(dow_s)*effect(weather_s)*spike_factor_s` (missing terms default to 1.0).
4) Deviations & tests:
   - Compute errors: `mae = mean(|lift_obs - lift_exp|)`, `mape = mean(|lift_obs - lift_exp|/max(lift_exp, eps))` across valid strata.
   - Optional statistical checks: fit GLM on `log(metric)` with factors for each influence; compare fitted coefficients to `log` of declared multipliers (Wald tests/confidence intervals).
5) Pass/fail:
   - Pass if `mae ≤ tolerance.mae` and `mape ≤ tolerance.mape`; otherwise report top‑N offending strata with counts, expected vs observed, and deltas.

Reporting:
- Include per‑influence marginals (e.g., DOW only, weather only) and full‑factor interaction table for inspected strata.
- Surface data sparsity warnings and which influences drove the largest deviations.

Notes:
- If the intended model is additive, the validator applies the same logic on the raw scale with `+` instead of `×` and uses difference errors instead of ratios.
- Robustness options (future): trimmed means, Winsorization, bootstrap CIs.

---

### Minimal Example (Domain‑Agnostic)
```json
{
  "version": "1.0",
  "metadata": {"name": "UniversalDemo"},
  "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-03-31T23:59:59Z", "freq": "H"},
  "nodes": [
    {
      "id": "user",
      "kind": "entity",
      "pk": "user_id",
      "columns": [
        {"name":"user_id","type":"int","nullable":false,"generator":{"sequence":{"start":1}}},
        {"name":"country","type":"string","nullable":false,
         "generator":{"choice":{"choices":["US","DE","IN","BR","GB"],"weights":[0.35,0.10,0.25,0.15,0.15]}}},
        {"name":"full_name","type":"string","nullable":false,
         "generator":{"faker":{"method":"name","locale_from":"country"}}},
        {"name":"address","type":"string","nullable":false,
         "generator":{"faker":{"method":"address","locale_from":"country"}}}
      ]
    },
    {
      "id": "event",
      "kind": "fact",
      "parents": ["user"],
      "pk": "event_id",
      "fanout": {"distribution":"poisson","lambda":4,"min":0,"max":20},
      "columns": [
        {"name":"event_id","type":"int","nullable":false,"generator":{"sequence":{"start":1}}},
        {"name":"user_id","type":"int","nullable":false,"generator":{"lookup":{"from":"user.user_id"}}},
        {"name":"ts","type":"datetime","nullable":false,
         "generator":{"datetime_series":{"within":"timeframe","freq":"H","pattern":{"dimension":"dow","weights":[0.9,1.0,1.0,1.1,1.3,1.2,0.8]}}},
         "modifiers":[{"transform":"time_jitter","args":{"std_minutes":20}}]},
        {"name":"amount","type":"float","nullable":false,
         "generator":{"distribution":{"type":"lognormal","params":{"mean":3.2,"sigma":0.7},"clamp":[1,500]}},
         "modifiers":[{"transform":"jitter","args":{"std":0.05,"mode":"mul"}},
                       {"transform":"clamp","args":{"min":1,"max":500}}]}
      ]
    }
  ],
  "constraints": {
    "unique": ["user.user_id","event.event_id"],
    "foreign_keys": [{"from":"event.user_id","to":"user.user_id"}],
    "ranges": [{"attr":"event.amount","min":1,"max":500}]
  },
  "targets": {"weekend_share":{"table":"event","timestamp":"ts","min":0.30,"max":0.45}},
  "dag": [["user"],["event"]]
}
```

---

### Guardrails
- Strict JSON Schema validation; reject unknown fields; clear error messages.
- Function whitelist (registry) only; no arbitrary imports or I/O.
- Deterministic seeding at node/column/parent scopes.
- Numeric clamp and explicit dtype casts after each pipeline.
- Preflight `--dry-run-sample` before full generation; auto‑retry with simplified plan on failure.

---

### Acceptance Criteria (MVP)
- Integrity: 100% PK uniqueness; 100% FK validity; ranges satisfied (post‑clamp).
- Realism: visible weekly/time‑of‑day patterns when configured; skewed amounts (lognormal) within clamps.
- Targets: example targets (e.g., weekend share) within bounds on sample and full runs.
- Determinism: same seed → identical outputs.
- Performance: generates 500k+ entity rows and corresponding fact rows within practical time on a laptop (chunked).

---

### Minimal Module Layout
- `core/schema.py` — Pydantic models + JSON Schema
- `core/dag.py` — dependency inference + toposort (NetworkX)
- `core/seed.py` — seed derivation helpers
- `core/generators/` — split executors
  - `primitives.py` — sequence/choice/distribution
  - `temporal.py` — datetime_series, seasonality
  - `semantic.py` — Faker/Mimesis adapters (names, addresses, etc.)
  - `registry.py` — function registry (ids → callables)
- `core/executor.py` — node orchestration (entities/facts), batching
- `core/validate/` — split concerns
  - `structural.py` — PK/FK/nullability/dtypes (optionally Pandera)
  - `behavioral.py` — seasonality/targets/composite effects
  - `reporter.py` — JSON + Rich console output (HTML later)
- `core/output.py` — Parquet + metadata
- `cli/commands.py` — create/generate/validate
- `llm/schema_generator.py` — optional NL→DSL
- `utils/locale_mapping.py` — country→locale (pycountry+babel)
- `utils/expression_eval.py` — numexpr + simpleeval wrappers (safe)



