# SKILL: tacc-agent-handoff (Holoscan Replay)

## Goal
Enable clean handoff for replay-mode Holoscan execution on TACC with explicit limits.

## Use This Skill When
- Running Holoscan replay workflows on shared HPC GPU nodes.
- Preparing a portability/limitations report versus live Sensor Bridge mode.

## Steps
1. Confirm replay dataset location and expected schema.
2. Prepare runtime environment and container strategy.
3. Execute replay pipeline via batch script.
4. Validate functional outputs and timing behavior.
5. Produce a limits report against live ingest expectations.
6. Report GPU efficiency to avoid under/over utilization of expensive allocations.

## Required Language in Reports
- "Replay validated" is allowed.
- "Live sensor path validated" is not allowed unless dedicated provisioning is explicitly documented.

## Known Risks
- Timestamp drift between recorded and runtime clocks.
- I/O throughput limits in shared storage paths.
- Misinterpretation of replay timing as hardware timing.
- GPU under-utilization from I/O bottlenecks or conservative replay rates.
- GPU over-utilization causing unstable tail latency and failed runs.

## GPU Usage Guidance
- Run smoke tests before long jobs to prevent wasted GPU-hours.
- Capture periodic GPU telemetry (utilization, memory, power) for every benchmark job.
- Track throughput per GPU-hour as a first-class metric.
- If utilization is consistently low, increase replay rate or reduce GPU count.
- If utilization is saturated with rising errors/tail latency, reduce replay rate or memory pressure.
