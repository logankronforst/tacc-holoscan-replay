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

## Required Language in Reports
- "Replay validated" is allowed.
- "Live sensor path validated" is not allowed unless dedicated provisioning is explicitly documented.

## Known Risks
- Timestamp drift between recorded and runtime clocks.
- I/O throughput limits in shared storage paths.
- Misinterpretation of replay timing as hardware timing.
