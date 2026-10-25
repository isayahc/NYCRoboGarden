# Embodied AI: research grounding and validation plan

NYC Robo Garden is an **engineering research platform**, not a demonstrated solution to general agricultural autonomy. The fixed seed-placement station is the first task to validate. The garden patrol is a kinematic visualization; it does not supply evidence of navigation, balance, perception or successful physical manipulation.

## Literature selection and interpretation

Literature was discovered through the connected **Valency research MCP service** on October 25, 2026, using semantic searches on agricultural robotics, sim-to-real transfer and adoption, followed by title/identifier lookups. Queries included “Open X-Embodiment Robotic Learning Datasets RT-X Models,” “Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics,” “Inner Monologue Embodied Reasoning,” and “agricultural robots adoption economic.” KOVIS was retrieved by identifier `2007.13960`. Publisher/proceedings and author-hosted records were checked for publication details. This is a selected reading list, not a systematic review or an exhaustive survey of the latest research. Relevance and proposed experiments below are our engineering interpretation, not claims that the authors tested NYC Robo Garden.

All seven selected works have peer-reviewed conference or journal versions. Open-access manuscripts are linked where useful; their posting/revision dates can differ from the publication year. Quantitative details below describe the cited work's scope, not prototype performance.

## Selected papers

### R1 — Generalization across robots, environments and tasks

**Open X-Embodiment: Robotic Learning Datasets and RT-X Models.** Open X-Embodiment Collaboration (Abby O'Neill et al.), **2024**, IEEE ICRA. [Paper and complete author list](https://arxiv.org/abs/2310.08864) · [Author project page](https://robotics-transformer-x.github.io/).

**Finding:** the collaboration assembled demonstrations from **22 robots and 21 institutions, covering 527 skills**, and demonstrated positive transfer across tested robots using pooled training data. **Relevance:** motivates reusable data formats and testing across seeds, trays and environments. **Limit:** cross-robot transfer on these evaluations is not proof that an SO-101 will handle an unseen seed or garden. We have not trained or evaluated RT-X in this repository.

### R2 — Sim-to-real and the reality gap

**Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics: a Survey.** Wenshuai Zhao, Jorge Peña Queralta and Tomi Westerlund, **2020**, IEEE SSCI, pp. 737–744. [DOI: 10.1109/SSCI47803.2020.9308468](https://doi.org/10.1109/SSCI47803.2020.9308468) · [Open manuscript](https://arxiv.org/abs/2009.13303).

**Finding:** reviews why policies trained in simulation encounter real-world mismatch and surveys domain randomization, domain adaptation and related transfer strategies. **Relevance:** motivates measuring the difference between rendered motions and actual arm/contact behavior. **Limit:** it concerns learned-policy transfer; our scripted kinematic animation is not even a dynamics-trained policy, so playing it successfully is not a transfer experiment.

### R3 — Visual servoing and successful manipulation

**KOVIS: Keypoint-based Visual Servoing with Zero-Shot Sim-to-Real Transfer for Robotics Manipulation.** En Yen Puang, Keng Peng Tee and Wei Jing, **2020**, IEEE/RSJ IROS. [DOI: 10.1109/IROS45743.2020.9341370](https://doi.org/10.1109/IROS45743.2020.9341370) · [Open manuscript](https://arxiv.org/abs/2007.13960).

**Finding:** a learned visual-servoing method using an eye-in-hand stereo camera transfers from simulation to selected physical grasping and insertion experiments, including a peg-in-hole task with **4 mm clearance** and M13 screw insertion. **Relevance:** motivates using visual feedback during approach and alignment, instead of treating a detected target as a completed action. **Limit:** 4 mm is the reported experimental clearance, not an accuracy bound or seed-placement result. KOVIS is described as calibration-free; that does not validate our different camera/arm arrangement or remove the need to measure its alignment.

### R4 — Contact and deformable-object manipulation

**Modeling of Deformable Objects for Robotic Manipulation: A Tutorial and Review.** Veronica E. Arriola-Rios, Puren Guler, Fanny Ficuciello, Danica Kragic, Bruno Siciliano and Jeremy L. Wyatt, **2020**, *Frontiers in Robotics and AI* 7:82. [DOI: 10.3389/frobt.2020.00082](https://doi.org/10.3389/frobt.2020.00082) · [Open article](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2020.00082/full).

**Finding:** reviews open problems in shape and material estimation, tracking, planning and control for deformable objects. **Relevance:** soil, leaves and seedlings need different assumptions from rigid animation props. Together with the gripper discussion in [R6](#r6--agricultural-robotics-and-deployment), this motivates separate tests of contact, seed singulation, slip and damage. **Limit:** the survey does not establish an SO-101 seed grasping method; seeds are not all deformable, and their small size is a separate handling constraint to measure.

### R5 — Long-horizon planning, feedback and recovery

**Inner Monologue: Embodied Reasoning through Planning with Language Models.** Wenlong Huang, Fei Xia, Ted Xiao, Harris Chan, Jacky Liang, Pete Florence, Andy Zeng, Jonathan Tompson, Igor Mordatch, Yevgen Chebotar, Pierre Sermanet, Tomas Jackson, Noah Brown, Linda Luu, Sergey Levine, Karol Hausman and Brian Ichter. **2023 proceedings of CoRL 2022**, PMLR 205:1769–1782. [Permanent proceedings page](https://proceedings.mlr.press/v205/huang23c.html) · [2022 preprint](https://arxiv.org/abs/2207.05608).

**Finding:** environment feedback, including success detection and scene descriptions, improved high-level instruction completion across **three tested domains**, including physical mobile manipulation in a kitchen. **Relevance:** motivates verifying outcomes and revising plans when observations disagree with expectations. **Limit:** feedback and an available skill repertoire are assumptions of the approach; a language planner does not itself supply a reliable gripper or calibrated uncertainty. Our scripted task order is not this planner.

### R6 — Agricultural robotics and deployment

**A Survey of Robotic Harvesting Systems and Enabling Technologies.** Leonidas Droukas, Zoe Doulgeri, Nikolaos L. Tsakiridis, Dimitra Triantafyllou, Ioannis Kleitsiotis, Ioannis Mariolis, Dimitrios Giakoumis, Dimitrios Tzovaras, Dimitrios Kateris and Dionysis Bochtis, **2023**, *Journal of Intelligent & Robotic Systems* 107, article 21. [DOI: 10.1007/s10846-022-01793-z](https://doi.org/10.1007/s10846-022-01793-z) · [Open manuscript](https://arxiv.org/abs/2207.10457).

**Finding:** reviews agricultural systems spanning vision, navigation, motion planning, human interaction, grasping and end-effector design, identifying autonomous harvesting as an open area. **Relevance:** crop detection is only a component of a physical workflow; unstructured gardens require integrated perception, access, manipulation and hardware evaluation. **Limit:** performance figures in individual reviewed systems are crop- and setup-specific. The review does not validate our mount, torque/payload limits, outdoor reliability or harvesting claims.

### R7 — Adoption economics and operational constraints

**How much can farmers pay for weeding robots? A Monte Carlo simulation study.** Linmei Shang, Christoph Pahmeyer, Thomas Heckelei, Sebastian Rasch and Hugo Storm, **2023**, *Precision Agriculture*. [DOI: 10.1007/s11119-023-10015-x](https://doi.org/10.1007/s11119-023-10015-x) · [Indexed abstract](https://pubmed.ncbi.nlm.nih.gov/37363790/).

**Finding:** models the purchase price at which weeding robots match existing-method profits for German sugar-beet farms. Capacity and weeding efficiency are influential for organic mechanical weeding; supervision intensity and herbicide savings matter for conventional spot spraying. Technology attributes were more influential than labor cost in the modeled acquisition values. **Relevance:** compare throughput, supervision, reliability and full ownership costs, not a kit price against a wage. **Limit:** modeled profitability in those farming systems does not establish savings for NYC seed trays, employment creation or equitable ownership.

## Physical validation plan

These are **proposed tests**, not completed results or literature-derived success thresholds. Agree on practical acceptance criteria with growers before trials. Keep all attempts, interventions and failures in the record, and identify the hardware, tooling, software revision and conditions used.

| Stage | Proposed evaluation and evidence | Gate before extending the claim |
| --- | --- | --- |
| Manual and mechanized baseline | Use the same seed/tray type; time preparation, seeding, cleanup and corrections. Compare manual work and a suitable vacuum tray seeder. | Record correctly seeded cells/hour, misses/doubles, damage, operator minutes and cost/successful tray. |
| Fixed hardware station | Measure camera-to-arm registration, reach/joint limits, repeatability and stop behavior; supervise initial movements. | No unattended execution until the configuration and recovery procedure have been evaluated. |
| Single-seed placement | Record continuous camera evidence of pickup, transport, release and cell occupancy, including uncertain/failed attempts. | Distinguish detection, pickup and verified placement rates; report trial counts and uncertainty, not only a highlight reel. |
| Contact and plant effects | Vary seed sizes, surfaces and tooling; measure slip, multiple pickup and visible damage; assess germination where appropriate. | A visually placed seed alone does not establish viability. Validate seedlings/leaves separately. |
| Generalization and recovery | Hold out seeds/trays/lighting; introduce occlusion, empty sources, missed pickups and displaced trays. | Bound retries; stop/escalate on uncertainty; report recovery and intervention rates. |
| Endurance and mobile mounting | Measure drift, wear, power, thermal limits, downtime, payload, mount security and stopping stability. | Station success does not authorize operation on a moving or unstable base. |
| Physical patrol | Validate surveyed routes, localization, obstacle response and return behavior before integrating a validated arm skill. | Obtain site permission and operating constraints; require evidence for each navigation and manipulation stage. |
| Community outcomes | Track access costs, skills demonstrated, maintenance effort, ownership, paid opportunities and grower net income. | Savings, jobs and equitable benefits remain hypotheses until evaluated with participants. |

Cost accounting should include hardware, tooling, compute, energy, setup/training, supervision, repair, downtime and failures. Do not double-count shared-arm hours or treat unpaid labor as having no time cost. Use the [README's existing alternatives and price references](../README.md#manual-work-mechanized-tools-and-our-proposed-approach) as initial comparisons, not a completed business case.

## Repository evidence boundary

Inspected against default-branch commit `7bc29df` after PR #29 merged. The implementation and tests establish software behavior, not physical success:

- [Patrol](../simulation/garden_patrol.py): scripted route and joint poses; calls `mj_forward`, not a balance controller.
- [Harvesting mission](../simulation/harvest_mission.py): bounded IK and scripted produce attachment/release; no measured grasp contact.
- [Simulation guide](garden-patrol.md): server-owned mission and simulated logs, separate from hardware evidence.
- [POV exporter](../scripts/render_patrol_pov.py): virtual chassis-relative camera only; no crop detector or navigation feedback.
- [Media record](media/README.md): exact seed-station source, optimized previews and pending hardware demonstration.
- Open [scene integration epic #4](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/4), [map-to-scene issue #8](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/8), [quality-gate issue #9](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/9) and [pilot issue #10](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/10) remain outstanding; documentation does not close their deployment requirements.
