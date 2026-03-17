flowchart TB
  %% AEL Architecture v0.1 (High Level)

  A["CLI / AI Agent"] --> B["Plan Generator"]
  B --> C["RunPlan (data only)"]
  C --> D["Runner (execution engine)"]

  subgraph E["Adapters (stateless step executors)"]
    E1["Build adapters\n(build.*)"]
    E2["Load adapters\n(load.* / run.*)"]
    E3["Check adapters\n(check.*)"]
  end

  D --> E1
  D --> E2
  D --> E3

  subgraph F["Hardware"]
    F1["Probe"]
    F2["Instrument(s)"]
    F3["DUT / Target Board"]
  end

  E1 --> F3
  E2 --> F1
  E2 --> F3
  E3 --> F2
  E3 --> F3

  D --> G["Recovery Engine (Runner-owned)"]
  G --> D

  D --> H["Artifacts (run folder)\nrun_plan.json, logs, measurements"]
  H --> I["Result Report\nresult.json + evidence"]

