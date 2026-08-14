Business Growth Simulator

A Python desktop application that models how strategic business decisions affect
revenue, costs, and profit over time, using Monte Carlo simulation to account for
market uncertainty.

- Overview

The app lets a user enter a company's starting financials, choose a set of strategic
decisions (hiring, expansion, automation, marketing), and select one or more market
scenarios to test against. It then runs hundreds of randomised simulations per
scenario to project a range of likely outcomes, rather than a single deterministic
forecast, and presents the results as charts, key metrics, and a written executive
summary.

- Features

- **Strategic decision modelling** — quantifies the growth and cost impact of four
  levers:
  - Hiring additional staff
  - Expanding into a new region
  - Automating a percentage of processes
  - Increasing marketing spend

  Each decision's effect on growth rate, costs, and (for expansion) risk is
  calculated by a dedicated impact calculator and shown to the user live as they
  adjust the sliders.

- **Monte Carlo simulation engine** — runs a configurable number of simulations
  (100–2000) per scenario, applying random year-on-year growth variation (drawn from
  a normal distribution scaled by a risk factor) to produce a distribution of
  outcomes rather than one fixed answer.

- **Five built-in market scenarios** — Recession, Stagnation, Normal Growth, Growth
  Phase, and Boom — each with its own growth modifier, cost modifier, and volatility,
  so the same strategic decisions can be tested against different economic
  conditions.

- **Results dashboard** — a four-panel chart view comparing scenarios:
  - Revenue growth over time
  - Net profit over time
  - Profit volatility (risk) by scenario
  - Final-year profit probability distribution

- **Automated executive summary** — generates a plain-English report covering base
  parameters, the effect of each strategic decision, per-scenario results, best/worst
  case outcomes, and risk considerations.

- **Data export** — summary CSV, full detailed CSV (every simulation/year
  combination), a text report, and chart images (PNG/PDF) can all be exported.

- **Runs on core Python** — includes a lightweight custom `SimpleDataFrame` /
  `SimpleGroupBy` implementation so the simulation and aggregation logic don't
  require pandas, keeping dependencies minimal.

- Tech Stack

- **Python 3.7+**
- **Tkinter / ttk** — GUI, including a scrollable input form and tabbed interface
- **matplotlib** — results charts, embedded in Tkinter via `FigureCanvasTkAgg`
- **NumPy** — random sampling for the Monte Carlo simulation and summary statistics
- **dataclasses, threading, csv, json** — from the standard library

- How It Works

1. The user enters base parameters (revenue, costs, employees, baseline growth rate,
   simulation length) and chooses strategic decisions via sliders and checkboxes.
2. A `DecisionImpactCalculator` converts those decisions into adjustments to the
   growth rate, annual costs, and risk factor.
3. For each selected market scenario, a `MonteCarloSimulator` runs the chosen number
   of simulations, applying the scenario's growth/cost modifiers plus random
   volatility each year, and records revenue, costs, and profit for every
   simulation/year.
4. Results are aggregated (mean, standard deviation, min, max) per year and scenario,
   then charted and summarised.
5. The simulation runs on a background thread so the UI stays responsive, with a
   progress bar reporting status.

- Running It

```bash
pip install matplotlib numpy
python business_simulator.py
```

Fill in the base parameters and strategic decisions on the first tab, select which
market scenarios to test, and click **Run Simulation**. Results appear on the
**Results & Charts** and **Summary & Export** tabs.

- Disclaimer

This is a learning project built to explore simulation, data modelling, and GUI
development in Python — projections are illustrative only and not intended as real
financial or business advice.


Author:
Anay Khole
