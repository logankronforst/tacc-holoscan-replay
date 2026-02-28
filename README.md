# TACC Holoscan Replay Experiment

This repository is for Holoscan replay-mode validation on TACC.

## Mission Context
This work supports spatio-temporal querying, dynamic Gym updates, and PIN-radio agent development for adversarial networking scenarios.

"Of course dont wish to spoil any weekend plans.... . Its integral, i believe to all our differential Hamiltonian Policy optimization learning, e.g. spatio-temporal querying of the environments by the mobile PIN-radio agent, as well as dynamic updates to the Gym too. Our group is developing PIN agents for dynamic adversarial networking response for the US Army."

## Feasibility on TACC
Status: Partial feasibility.

## Critical Limitation (Explicit)
This repo targets replay/software validation only unless TACC provides dedicated provisioning for live sensor paths.

### Not guaranteed on standard shared HPC nodes
1. Live Sensor Bridge ingest from external sensor hardware.
2. Sub-microsecond time sync validation (PTP end-to-end).
3. Hardware-timed NIC/sensor pipeline equivalence to edge deployment.

## What is feasible
1. Holoscan graph execution with recorded data replay.
2. Operator-level profiling and throughput analysis.
3. Pipeline correctness checks for multi-modal processing.

## If full live mode is needed
Require dedicated provisioning:
1. Reserved hardware/network topology.
2. Sensor interface access.
3. PTP/time-sync-enabled network path.
4. Permissions/runtime support for low-level I/O paths.

## Handoff
See `AGENTS.md` and `skills/tacc-agent-handoff/SKILL.md`.
