# NEXUS RISKCAST v2.0

> **Decision Intelligence Platform for Supply Chain Risk Management**

## Overview

NEXUS transforms supply chain information into actionable decisions. Unlike notification systems that tell you *what happened*, RISKCAST tells you *what to do*.

```
OMEN (Signals) → ORACLE (Reality) → RISKCAST (Decisions) → Alerter (WhatsApp)
```

## The 7 Questions

Every RISKCAST decision answers:

| # | Question | Example Output |
|---|----------|----------------|
| Q1 | What's happening? | "Red Sea disruption affecting YOUR route SH→RTM" |
| Q2 | When? | "Impact starts in 3-5 days for shipment #4521" |
| Q3 | How bad? | "Your exposure: $235K across 5 containers" |
| Q4 | Why? | "Houthi attacks → carriers avoiding Suez → +10 day delay" |
| Q5 | What to do? | "REROUTE NOW via Cape. Cost: $47K. Carrier: MSC" |
| Q6 | Confidence? | "87% based on 3 sources + 23 vessels rerouting" |
| Q7 | If nothing? | "Wait 6h → cost becomes $89K. Wait 24h → miss booking" |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload

# Run tests
pytest
```

## Project Structure

```
app/
├── core/           # Config, database
├── omen/           # Signal engine (predictions)
├── oracle/         # Reality engine (ground truth)
├── riskcast/       # Decision engine (THE MOAT)
│   ├── schemas/    # Data models
│   ├── matchers/   # Exposure matching
│   ├── calculators/# Impact calculation
│   ├── generators/ # Action generation
│   └── composers/  # Decision composition
└── alerter/        # Delivery (WhatsApp)
```

## The Moat

Our competitive advantage is **customer context**:

- Day 1: Generic alerts (competitors can copy)
- Day 30: Personalized decisions (know their routes, shipments)
- Day 90: Self-improving system (historical accuracy)

## Tech Stack

- Python 3.11+
- FastAPI + Pydantic v2
- PostgreSQL + Redis
- WhatsApp Business API

## License

MIT
