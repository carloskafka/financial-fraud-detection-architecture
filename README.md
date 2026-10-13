# Real-Time Financial Fraud Detection Architecture

This repository contains a reference solution architecture for a low-latency,
high-volume fraud analysis platform. The final submission is
[`architecture-report.pdf`](architecture-report.pdf); its editable source is
[`architecture-report.md`](architecture-report.md), with editable Graphviz
diagrams in `diagrams/`.

## Contents

- Functional microservice decomposition, contracts, inputs/outputs, and event
  triggers.
- Solution, event-flow, end-to-end transaction, and deployment/recovery
  diagrams.
- Technology choices, analyst frontend/BFF design, scaling approach, and
  measurable SLOs.
- Observability design for logs, metrics, traces, correlation, dashboards, and
  paging.
- Replay/evidence retention, resilience and recovery, security controls, and
  financial-services trade-offs.

## Rebuild the PDF

Requires Python 3.8+, Graphviz (`dot`), and the dependencies in
`requirements-docs.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-docs.txt
for f in diagrams/*.dot; do
  dot -Tpng -Gdpi=160 "$f" -o "${f%.dot}.png"
done
python scripts/build_pdf.py
```

The report treats retention periods, RPO/RTO, alert thresholds, and the
authorization fail-open/hold policy as decisions for the institution's legal,
fraud, risk, and payment owners to confirm. Targets in the report are proposed
engineering objectives, not claims of measured production performance.
