## mt5-ai-trading-supervisor

Controlled MT5 execution supervisor: **signals in, deterministic validation + hard risk gates, audited execution out**.

### Design constraints (non-negotiable)

- **Execution authority**: Python is the only execution layer; EAs/sources produce signals only.
- **Deterministic hard risk**: hard risk rules are final and deterministic; adaptive logic can only suggest.
- **Strong safety architecture**: master authority, manual overrides, safe baseline, rollback, observability.
- **Auditability**: every decision and action is reconstructable from structured records.
- **Spread correctness**: when generating synthetic spreads, always generate **in points** and convert with:
  - \(spread\_price = spread\_points \times symbol\_point\)

### Local setup

- **Python**: 3.11+
- **Install**:

```bash
cd mt5-ai-trading-supervisor
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

- **Config**:
  - Copy `.env.example` to `.env` and edit as needed.

### Run

Entry point is `trading_supervisor/main.py` (Phase 1–2 only provides models + foundation).

```bash
cd mt5-ai-trading-supervisor
python -m trading_supervisor.main
```

### Tests

```bash
cd mt5-ai-trading-supervisor
pytest
```

