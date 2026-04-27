# Mode Policy Capsule

| Mode | Pipeline | Intended Use |
|---|---|---|
| Fast | single translation + deterministic structure/glossary checks | draft / internal review only |
| Normal | differentiated Pass A + Pass B + synthesis + gates | default delivery path |
| Hard | Normal + back-translation + Library top-K comparison + editorial review | external or high-risk delivery |

Pass A is source-faithful legal literal translation. Pass B is target-jurisdiction legal drafting translation. Synthesis selects against source, structure, and glossary; never by simple majority.

Every new job manifest must include `mode_plan` so the selected mode is auditable:

| Mode | Final Step | Required Model Calls | Conditional Calls |
|---|---:|---:|---:|
| Fast | 5 | 1 | 0 |
| Normal | 7 | 3 | 0 |
| Hard | 10 | 5 | 1 Library comparison, only when matching Library assets exist |
