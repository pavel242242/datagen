# Datagen - Project Goals & Vision

> **Last Updated**: 2025-11-09
> **Current Phase**: Phase 4 - Advanced Analytics Features (2 of 3 CRITICAL features shipped)

---

## 🎯 Vision Statement

**Datagen is the universal, schema-first synthetic data generator that makes realistic test data as easy as writing JSON.**

We enable data engineers, scientists, and developers to create deterministic, multi-table datasets with realistic behavioral patterns—without writing code. Long-term: natural language descriptions → production-ready schemas via LLM integration.

---

## 🏆 Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Test Pass Rate** | 95/95 (100%) | 100% | ✅ |
| **Test Coverage** | 43% | 75% | ⚠️ In Progress |
| **Quality Score** | 95.4/100 (bank schema) | 95+ | ✅ |
| **Performance** | 500K rows in ~10s | 1M rows in <20s | ✅ |
| **Feature Completeness** | Phase 4: 3/3 CRITICAL | Phase 4: 3/3 | ✅ Complete! |
| **LLM Integration** | Planned | Production-ready | 📋 Phase 5 |

---

## 🚀 Current Phase: Phase 4 - Advanced Analytics Features

### ✅ Recently Shipped (Validated via Blind Analysis)

**Feature #7: Time Series Trends** (2025-11-09)
- Impact: Revenue forecasting R² improved **78.5x** (0.0014 → 0.11)
- Capability: Exponential/linear/logarithmic growth/decay trends
- Validation: VP of Growth analysis shows "Growth Story Has Three Distinct Phases"

**Feature #2: Entity Segmentation** (2025-11-09)
- Impact: Enables profitability analysis and targeted strategies
- Capability: Behavioral clusters with segment-specific multipliers
- Validation: VIP segment shows 22 orders/customer vs Standard 21.6

### ✅ SHIPPED: Feature #1 - Entity Vintage Effects (2025-11-09)

**Status**: ✅ SHIPPED - Phase 4 CRITICAL feature complete
**Effort**: 12 hours total (implementation 8h + validation 2h + temporal fix 2h vs estimated 12-16h)
**Impact**: CRITICAL - Enables cohort retention analysis, LTV, churn measurement

**Problem Solved**: "All users signed up at once - can't measure true churn or cohort retention"

**What It Enables**:
- Cohort-based retention analysis ✅
- Customer lifetime value (LTV) calculations ✅
- Realistic churn patterns over time ✅
- Age-based activity decay curves ✅
- Vintage analysis across any entity type ✅

**Implementation Complete**:
- ✅ `src/datagen/core/vintage_utils.py` - 300 lines (age calc, curve evaluation)
- ✅ `src/datagen/core/schema.py` - vintage_behavior field added
- ✅ `src/datagen/core/executor.py` - Age multipliers + temporal constraint (lines 348-402)
- ✅ `tests/test_vintage_effects.py` - 27 comprehensive tests (all passing)
- ✅ 4 example schemas across domains:
  - E-commerce: `examples/vintage_effects_demo.json`
  - SaaS: `examples/saas_subscription_vintage.json`
  - Healthcare: `examples/healthcare_appointments_vintage.json`
  - Manufacturing: `examples/manufacturing_sensors_vintage.json`

**Validation Complete** (3 parallel haiku agents + 4 domain tests):
- ✅ VP Growth detected: "Early cohorts 10-20x more valuable" (19x LTV difference measured)
- ✅ Head of Data detected: "75% engagement decay over customer lifetime"
- ✅ Both analysts built cohort retention analyses unprompted
- ✅ Temporal constraint fixed: 100% compliance (34,534 events, 0 violations)
- ✅ Domain-agnostic design validated across SaaS, Healthcare, Manufacturing

**Full Reports**:
- `BLIND_ANALYSIS_FINDINGS_FEATURE1.md` (blind validation)
- `docs/validation/feature-1-vintage-effects/` (agent reports)

---

## 📋 Backlog (Post-Feature #1)

### HIGH Priority - Phase 4 Completion
- **Feature #3**: Multi-Stage Processes (conversion funnels, user journeys)
- **Feature #4**: Recurring Relationships (subscription lifecycle, state transitions)

### MEDIUM Priority - Phase 4 Nice-to-Have
- **Feature #5**: Multi-Touch Attribution (marketing ROI, channel optimization)
- **Feature #6**: Diffusion/Adoption Curves (S-curves, viral spread)

### Phase 5 - LLM Integration (Q1 2026)
- Natural language → JSON schema conversion
- Schema validation loop with auto-repair
- Clarification questions for ambiguous specs

---

## 💎 Core Design Principles

These are **non-negotiable** - all features must align:

1. **Schema-First** - Declarative JSON DSL, never code generation (safer for LLMs)
2. **Deterministic** - Same seed always produces identical data
3. **Domain-Agnostic** - No business logic, only generic patterns (works for any industry)
4. **Relational** - Multi-table with enforced FK integrity
5. **Validated** - Comprehensive quality scoring built-in
6. **Realistic** - Behavioral patterns, not just random distributions
7. **Fast** - Vectorized (NumPy/Pandas), not row-by-row

---

## 🎓 Target Users

| Persona | Primary Use Case | Key Need |
|---------|------------------|----------|
| **Data Engineers** | Test data pipelines, staging environments | FK integrity, determinism |
| **QA/Testing Teams** | Performance testing, regression testing | Large-scale realistic data |
| **Data Scientists** | Training datasets, reproducible research | Deterministic, behavioral patterns |
| **Analytics Teams** | Demo datasets, sandbox analysis | Realistic trends, segmentation |
| **Developers** | Local dev with realistic data | Fast generation, simple schemas |

---

## 📊 Quality Dashboard

### Test Health
- ✅ **69/69 tests passing** (100% pass rate)
- ⚠️ **43% coverage** → Need 32-point improvement to reach 75% target
- ❌ **Validation module**: 0% coverage (549 lines untested - CRITICAL)
- ⚠️ **Modifiers**: 35% coverage (6+ modifiers need tests)
- ❌ **CLI commands**: 0% coverage (user-facing untested)

### Code Quality
- ⚠️ **14 files** need black formatting
- ⚠️ **47 linting issues** (ruff)
- ❌ **No CI/CD** (GitHub Actions needed)
- ❌ **No pre-commit hooks**

### Documentation
- ✅ Comprehensive CLAUDE.md (architecture)
- ✅ Complete datagen_spec.md (DSL reference)
- ⚠️ 41 markdown files in root (needs reorganization)
- ⚠️ No unified PRD (scattered across multiple docs)

---

## 🛠️ Quick Reference

### Essential Commands
```bash
# Development
pytest tests/ -v                  # Run all tests
pytest tests/test_generators.py   # Test specific module
coverage run -m pytest tests/     # Run with coverage
coverage report                   # Show coverage

# Code Quality
black src/ tests/                 # Format code
ruff check src/ tests/            # Lint code
ruff check --fix src/ tests/      # Auto-fix issues

# Generation & Validation
datagen generate examples/simple_users_events.json --seed 42
datagen validate examples/simple_users_events.json --data ./output
```

### Key Files
- `CLAUDE.md` - Architecture guide (read this first!)
- `datagen_spec.md` - Complete DSL specification
- `GOAL.md` - This file (current state & priorities)
- `PRD.md` - Feature roadmap and status
- `src/datagen/core/executor.py` - Main generation engine
- `src/datagen/core/schema.py` - Pydantic DSL models

---

## 🎪 Development Workflow

1. **Check current priority** - Read this file (GOAL.md)
2. **Verify test baseline** - Run `pytest tests/ -v`
3. **Implement with tests** - Aim for 80%+ coverage on new code
4. **Format & lint** - `black src/ tests/` and `ruff check --fix src/ tests/`
5. **Validate** - Generate example schemas, run validation
6. **Commit** - Clear message following existing patterns

---

## 🚨 Current Blockers & Risks

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| Low test coverage (43%) | Medium | Incremental improvement, target 75% |
| Validation module untested | HIGH | Priority after Feature #1 |
| No CI/CD | Medium | Add GitHub Actions in Phase 4 cleanup |
| Feature #1 complexity | HIGH | Break into sub-tasks, thorough testing |
| 41 docs in root | Low | Reorganize after Feature #1 ships |

---

## 💡 What Makes Datagen Unique

**vs. Code-based tools** (Synthpop, Mostly AI):
- ✅ No Python code generation (safer, auditable)
- ✅ LLM-compatible (schemas, not code)
- ✅ Deterministic by default

**vs. Traditional tools** (Faker, mockaroo):
- ✅ Multi-table with FK integrity
- ✅ Behavioral realism (segments, trends, vintage effects)
- ✅ Quality validation built-in

**vs. ML-based tools** (Gretel, Tonic):
- ✅ Lightweight (no model training)
- ✅ Fast (seconds, not minutes)
- ✅ Simple (JSON, not complex UI)

---

## 🎯 Immediate Next Steps

1. **Implement Feature #1: Entity Vintage Effects** (12-16h)
   - Add schema support for vintage_behavior
   - Implement age-based multipliers in executor
   - Create comprehensive test suite
   - Validate with blind analysis

2. **Increase test coverage to 60%+** (post-Feature #1)
   - Add validation module tests (0% → 80%)
   - Add modifier tests (35% → 80%)
   - Add CLI integration tests (0% → 70%)

3. **Set up CI/CD** (after coverage improvement)
   - GitHub Actions for automated testing
   - Pre-commit hooks for formatting
   - Coverage baseline tracking

---

**🔥 Focus**: Feature #1 (Vintage Effects) is the critical path to Phase 4 completion. All other improvements can wait until this ships and validates.

**📈 Success Looks Like**: Blind analyst can perform cohort retention analysis and say "retention drops 30% after 6 months" with realistic data supporting it.
