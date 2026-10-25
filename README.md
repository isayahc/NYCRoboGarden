# Spooky Civic AI Hackathon

**Project: NYC Robo Garden**

**Selected track: Physical AI for Good**

Built for the [Spooky Civic AI Hackathon: Build Weekend](https://luma.com/onzzmytl), hosted by 3percentclub in NYC and online, October 23–24, 2026, with Demo Day on October 25.

## Problem statement

**NYC Robo Garden aims to help small farms and community gardens automate repetitive manual tasks while giving people at every stage of life a practical way to learn robotics and AI.** Seed-tray planting is our initial physical task; the simulated mobile arm explores how the same planning concepts could extend to tending and harvesting. The goal is to lower the cost, technical knowledge, and integration effort needed for smaller growers to experiment with automation, one useful task at a time.

### Why this matters for small farms

- **Small farms are the majority:** small family farms accounted for **86% of U.S. farms and 40% of agricultural land in 2024**, but 17% of production value. USDA defines this group by gross cash farm income below $350,000, not acreage. These national figures establish the broader context; they do not measure NYC community gardens. [USDA ERS](https://www.ers.usda.gov/data-products/charts-of-note/114161)
- **Labor is a substantial production expense:** wages, salaries, and contract labor represented **42% of greenhouse and nursery production expenses and 40% for fruit and tree nuts**, compared with 12% across all farms in the 2022 Census of Agriculture. [USDA ERS — Farm Labor](https://www.ers.usda.gov/topics/farm-economy/farm-labor)
- **Reliable agricultural robotics remains an active science and engineering problem.** USDA's 2026 research summary describes ongoing work on field sensing, robotic manipulation, mechanization, and adoption. One reported apple-harvesting system achieved approximately **70% picking success** despite reported 100% detection accuracy in its evaluation: recognizing a target and successfully manipulating it are different challenges. This is a result for that system, not an industry-wide benchmark. [USDA NIFA — Automation for Specialty Crops](https://www.nifa.usda.gov/about-nifa/impacts/automation-specialty-crops)

Our research question is concrete: can a grower configure a small robot to locate seeds, place one in each tray cell, verify the result, and recover from misses with sufficiently little supervision to be useful? We start with a bounded workstation, reusable software, and simulation before extending to variable lighting, plant shapes, soil, and mobile operation. Shared equipment and training through gardens, schools, and grower cooperatives are proposed ways to spread access and fixed costs.

### Manual work, mechanized tools, and our proposed approach

There is a spectrum of existing options. Equipment prices below are **USD listings checked October 24, 2026**, before applicable tax, shipping, and dealer charges. Wage figures are **2024 U.S. averages**, not current NYC quotes or fully loaded employer costs.

| Approach | Published cost reference | Specialization and reuse | Human work and task fit |
| --- | --- | --- | --- |
| Manual crop, nursery, and greenhouse work | **$18.24/hour** average wage. Ten person-hours = **$182.40 in wages**, calculated before employer overhead. [USDA ERS](https://www.ers.usda.gov/topics/farm-economy/farm-labor) | Broadly adaptable skills; new tasks may require training. | Flexible handling and judgment; a person performs the task. Family and volunteer labor also consumes time even without a wage payment. |
| Human-powered precision field seeding: Jang JP-1 | **$495**, with the required seed roller sold separately. [Johnny's](https://www.johnnyseeds.com/tools-supplies/seeders/jang-jp-series/jang-jp-1-push-seeder-7319.html) | **Specialized field seeder.** Rollers adapt seed size and spacing within the same task. | Operator pushes and steers; seeds prepared field rows rather than plug trays. An existing option for small growers. |
| Mechanized tray seeding: Precision Vacuum Seeder | **$727**, including a small shop vacuum; seed plates sold separately. [Johnny's](https://www.johnnyseeds.com/tools-supplies/seeders/vacuum/precision-vacuum-seeder-7335.html) | **Specialized tray seeder.** Different plates adapt tray/seed formats; it remains a seeding machine. | Operator loads, handles, and aligns the seeder. Supplier advertises up to **120 trays/hour**; this is a supplier claim, not our measured result. A direct baseline for our seed-tray task. |
| Powered small-farm machinery: BCS 718 walk-behind tractor | **$3,200** tractor + **$890** compatible 18-inch tiller = **$4,090 MSRP** before fees. [BCS configurator](https://www.bcsamerica.com/build-your-bcs) · [718 compatibility](https://www.bcsamerica.com/product/model-718) | **Multipurpose power unit with specialized attachments.** Additional implements add cost and have model-specific compatibility. | Requires an operator, fuel, and maintenance. Illustrates the cost of powered soil preparation; it does **not** perform the seed-tray task. USDA's separate 2024 equipment-operator wage average is **$19.07/hour**. |
| NYC Robo Garden: configurable robotic workstation, with mobile operation explored in simulation | **Arm price references: $121.94 DIY follower parts or $184.99 follower kit; see breakdown below. Full installed cost and cost per completed task remain unmeasured.** Include arm, cameras, tooling, workstation, compute, power, setup, maintenance, and any physical mobile base. | **Reprogrammable manipulation platform.** New tasks can reuse the arm but may need different tooling, fixtures, sensing, and software. | Intended to combine sensing, task planning, action, and verification, with people configuring and supervising. Current demonstrations do not establish autonomous farm reliability or labor savings. |

**Affordability must be demonstrated against the appropriate existing tool.** A dedicated vacuum seeder may be faster and cheaper for repeated tray seeding. Our proposed value is adaptable tasks, observable execution, and a platform people can learn to modify and maintain. Compare the same tray and seed type using correctly seeded cells per hour, misses/doubles, seed damage, operator minutes, setup time, and total cost per successful tray. Purchase price alone cannot establish savings against an hourly wage.

### What the SO-101 arm costs

We use an **SO-101 leader/follower setup**: the follower performs the work, while the leader provides a physical interface for demonstrations and teleoperation. The prices below are reproduction-cost references, **not a verified invoice for the Viam-provided hardware**. Configurations differ, including servo voltage.

| SO-101 configuration | USD reference price | Included scope and exclusions |
| --- | --- | --- |
| One follower, sourced from the upstream bill of materials | **$121.94** | Listed 7.4V-servo parts, controller, power supply, cables, clamps, and tool allowance. Printed structure, assembly labor, cameras, and computer are additional. |
| Leader + follower, upstream bill of materials | **$229.88** | Two-arm parts list; printed structures and the rest of the workstation are additional. |
| ForgeMotion follower-arm kit | **$184.99** | Vendor lists printed frame, compliant gripper, camera mount, and 12V electronics. A camera mount is not a camera. |
| ForgeMotion complete teleoperation kit | **$339.99** | Vendor lists leader + follower arms and electronics as a kit; this is not a complete autonomous farm workstation. |

Sources checked October 24, 2026: [upstream SO-101 bill of materials](https://github.com/TheRobotStudio/SO-ARM100#sourcing-parts) and [ForgeMotion kit listings](https://forgemotionlabs.com/products). Add applicable shipping and tax. Do not treat the two-arm teleoperation kit as two independent productive arms; the leader is the teaching/control interface.

### Why specialization changes the economic comparison

**A programmable arm offers the possibility of sharing one hardware investment across multiple tasks and learning activities.** Seed placement, sorting, and light pick-and-place are candidate uses within its mechanical limits. Each needs its own validated workflow; programmability alone does not supply a reliable new skill. Upstream designs include alternative mounts and grippers, supporting hardware adaptation. [SO-101 project](https://github.com/TheRobotStudio/SO-ARM100)

For a grower, compare both **cost per successful task** and **annual use across validated tasks**. Include attachment/tool costs, programming or demonstration time, calibration, changeovers, supervision, maintenance, and failures. Spread the shared arm's ownership cost across its actual productive use without double-counting hours; tasks competing for the same arm cannot run simultaneously. A specialized seeder can win on speed and simplicity, while a reusable arm may become attractive when several suitable tasks keep it productively occupied. The BCS tractor also offers reuse through attachments, so versatility is not unique to robots.

The SO-101's flexibility is in light manipulation. It does not make it a replacement for the tractor's soil-working power, nor establish outdoor durability, harvesting ability, or a production duty cycle. Our hypothesis is that affordable, adaptable hardware plus practical training can lower entry barriers; the comparison must measure both task performance and the effort required to adapt it.

### A practical learning pathway at every stage of life

A visible task—moving a seed into the correct tray cell—connects AI predictions to a result learners can inspect. The intended learning pathway welcomes school-age learners with appropriate supervision, students, working adults, career changers, and older adults, with activities adapted to experience and accessibility needs.

| Learning activity | Robotics and AI concepts | Concrete learner output |
| --- | --- | --- |
| Describe how a person plants a tray and define success | Task decomposition, requirements, and measurement | A task checklist and manual baseline |
| Run and change the simulated garden mission | Coordinates, joint limits, motion planning, and state machines | A modified mission with an explanation of its motion |
| Inspect camera views and label seeds and tray cells | Data collection, computer vision, uncertainty, and evaluation | An annotated dataset and detection-error report |
| Calibrate and test a supervised arm at a fixed station | Camera-to-robot calibration, end effectors, control, and safe stopping | A measured placement trial, including failed attempts |
| Compare approaches and improve the workflow | Experiment design, debugging, maintenance, and unit economics | Evidence showing whether a change improves accuracy, effort, or cost |

The repository already supplies simulation, scene-authoring, and camera/connection tools to support this pathway. The complete teaching program and reliable seed-placement workflow are development goals; learning outcomes have not yet been evaluated.

### Economic growth and equitable wealth generation

The intended economic pathway is to help growers retain more value from their work while enabling local people to **build, adapt, operate, repair, and potentially own the automation**. Practical experience could support paid installation and maintenance work, agricultural technology services, and small businesses. Shared workshops, community-owned equipment, and cooperative service models could let growers and workers participate without each buying a complete system.

Equitable wealth generation is a design objective: involve farmworkers in task selection and training, make participation affordable, and give communities a role in ownership and decisions about productivity gains. Evaluate that objective through access costs, demonstrated skills, paid opportunities, grower net income, and who owns the equipment. These are proposed mechanisms and measures, not proven employment or income outcomes from this hackathon prototype.

## Start the autonomous farm demo

```bash
pip install -r requirements-simulation.txt
python -m simulation.server
```

Open **http://127.0.0.1:8080**. The ASTRA dog carries the mounted SO-101 arm,
walks to three crop beds, picks a carrot, lettuce and tomato, places each in its
collection box, and returns home. The 72-second harvesting mission repeats continuously.
The server owns the mission; opening or refreshing the dashboard does not restart it.
The browser renders the actual robot meshes with Three.js/WebGL, interpolating
30 Hz pose updates at the display refresh rate. Drag to orbit, scroll to zoom,
or use **Follow action**. The backend does not render or encode video frames.
This is a **kinematic simulation** with scripted produce attachment/release and
joint-limited inverse kinematics, not physical robot control or grasp-contact validation.
See [the farm mission guide](docs/garden-patrol.md#server-driven-harvesting-mission).

## Hackathon tracks

### Selected — Physical AI for Good

**This is NYC Robo Garden's selected track.** Build AI that acts in the physical world, with robot-arm kits available onsite and no prior robotics experience required.

| Other track | Focus |
| --- | --- |
| The Existential Track | Climate and sustainability: heat, waste, food access and cleaner air |
| Urban Nightmares | Housing, healthcare, education and justice |
| Ghost in the Machine | Search, data and infrastructure for civic tools |

NYC Robo Garden also relates to sustainability and food access; its selected competition track is **Physical AI for Good**.

## NYC Robo Garden — Urban Agriculture Network

NYC Robo Garden explores how community-oriented agricultural robotics could support urban growers, education, and shared food-growing spaces. New York City has many community gardens, but **a listed garden is not necessarily a greenhouse, an active food-production site, or an approved robotics deployment location**.

### Find gardens and urban agriculture sites

| Resource | What it provides | How we could use it |
| --- | --- | --- |
| [NYC Parks GreenThumb](https://www.nycgovparks.org/greenthumb) | Official NYC community-gardening program | Learn about participating gardens and community stewardship |
| [NYC GreenThumb Garden Info (NYC Open Data)](https://data.cityofnewyork.us/dataset/GreenThumb-Garden-Info/p78i-pat6) | Public garden records, including geospatial information | Build a filterable site-discovery map |
| [GreenThumb garden locations (GeoJSON)](https://data.cityofnewyork.us/resource/p78i-pat6.geojson) | Machine-readable garden geography | Load candidate points into GIS or a web map; check API pagination/limits before assuming complete coverage |
| [NYC Mayor's Office of Urban Agriculture](https://www.nyc.gov/site/agriculture/) | Citywide urban-agriculture programs and resources | Discover urban farming partners and additional site information |
| [New York Restoration Project — Community Gardens](https://www.nyrp.org/en/get-involved/community-gardens/) | Community gardens supported by NYRP | Identify potential organizational partners |

### Interactive NYC garden map

**[Open the NYC Garden Explorer](docs/gardens-map/index.html)** — Leaflet-based map using the live NYC GreenThumb dataset with borough, status, and name/address filters. The interactive page is stored at `docs/gardens-map/index.html`. To serve it publicly, enable **GitHub Pages → Deploy from branch → main → /docs** after merging. The published URL will be `https://isayahc.github.io/Spooky-Civic-AI-Hackathon/gardens-map/` once Pages is configured.

The application fetches the NYC Open Data records when opened, so it requires internet access to the Socrata endpoint and OpenStreetMap tile provider. Garden markers are public dataset records, not verified greenhouse sites or deployment permissions. This first version is a **2D site-discovery map**; 3D Open-Industries generation is tracked separately in [epic #4](https://github.com/isayahc/Spooky-Civic-AI-Hackathon/issues/4).

### Versioned garden data

The [garden registry pipeline](docs/garden-registry.md) ingests GreenThumb records into typed, versioned data with stable Parks IDs, source metadata and deduplication. It keeps location points, source polygons and optional BBL-matched tax lots distinct.

```bash
python3 -m garden_registry --output data/generated
python3 -m unittest discover -s tests -v
```

### Layout, infrastructure and produce evidence

The [evidence research contract and importer](docs/garden-evidence.md) attach dated, cited claims to registry sites while keeping ambiguous matches and unknowns separate. The initial sample includes a historical bed-addition report; it does not establish current layouts or utility availability.

### Mounted arm garden patrol demo

[Watch the robot dog carry the SO-101 arm around three garden beds](docs/media/garden-patrol.mp4). [Run the interactive model or export a video](docs/garden-patrol.md). This uses the actual robot meshes and a fixed mount, with scripted leg motion and a closed patrol route. It is kinematic playback in a fictional garden; physical balance and payload capacity are not validated.

### Generate an Open-Industries scene

The [garden scene adapter](docs/garden-scene-adapter.md) converts an explicit garden manifest into OI-native LOD0/LOD1 geometry, preserves evidence and WGS84 georeferencing, and supports OI 3D Tiles export plus MCP asset bindings. Start with the clearly fictional fixture:

```bash
python3 -m garden_registry.scene_adapter build data/scenes/fictional-garden.json --output data/generated/garden-demo
python3 -m garden_registry.scene_adapter reload data/generated/garden-demo
```

A real registry record needs an explicitly sourced footprint before generation. Procedural surfaces and envelopes remain labeled inferred.

### Proposed pilot-site screening

Start with **Brooklyn** and expand across the five boroughs. Evaluate candidate locations using information confirmed by the site operator:

- Garden name, location, contact organization, and permission to engage
- Food-growing activities and whether a greenhouse or controlled-environment space exists
- Water, electrical power, connectivity, and physical access
- Robot operating area, pedestrian access, supervision, and safety constraints
- Community value: education, tending, monitoring, harvesting, and shared meals

### Potential applications

- Environmental and soil sensing
- Assisted watering and garden maintenance
- Documented robotic task demonstrations
- Plant monitoring and educational workshops
- Farm-to-kitchen community events

**Project status:** These are discovery resources and candidate evaluation criteria, not confirmed deployment partners. Site suitability, permissions, and greenhouse availability require direct verification.

## Event logistics and submission

All times are **Eastern (New York)**.

| Date | Location | Milestones |
| --- | --- | --- |
| Friday, October 23 | Civic Hall, 124 E 14th St, Room 615 | Physical AI starts 11am; arm teams check in by 2pm. All-track kickoff 6pm; close 8pm. |
| Saturday, October 24 | Jay Conference Bryant Park, 109 W 39th St, second floor | Doors 10:30am; close 5pm. **Submit by 11:59pm: repository, demo video, short write-up.** |
| Sunday, October 25 | Luma Studios, 307 W 38th St, Studio 1701 | Demo Day 2–5pm; top five present onstage. [Separate RSVP](https://luma.com/3perce-pi2u). |

Teams have 2–5 members; robot-arm teams have 3–5. No solo projects. Arms remain onsite; remote development is allowed. Physical AI participants should create a [Viam account](https://app.viam.com/).

Awards include a robot-arm kit, best overall, fellows-only cash and recruiter session, People's Choice, costume contest and Miss Congeniality. The event page does not specify the cash amount or scoring rubric.

## Sponsor configuration

Copy the template without overwriting an existing local configuration:

```bash
cp -n example.env .env
```

Fill in only the services you use. See [example.env](example.env) for credential sources and optional fields.

| Sponsor | Configuration |
| --- | --- |
| Viam | Machine address, API key and key ID from the machine's CONNECT tab. Component names are optional and must match the configured hardware. |
| Tavily | API key from the Tavily dashboard for authenticated API requests. |
| Vonage | API key/secret or application ID/private key, depending on the API. Signature secret is only for applicable signed webhook/message verification. |

Keep the Vonage private key in `secrets/` and set `VONAGE_PRIVATE_KEY_PATH` to its local file path. Local `.env` files and `secrets/` are ignored by Git; commit only blank templates.

This is configuration scaffolding. Application code must load the environment and pass these values to the sponsor SDKs; copying the file alone does not enable an integration. Keep credentials server-side. Channel-specific sender numbers, recipients and callback URLs can be added once the Vonage feature is selected.

## Sponsors and project use

The event lists **Viam, Vonage and Tavily** as official partners. Their event contributions are distinct from our project's integrations.

### Viam

<a href="https://www.viam.com/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/sponsors/viam-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/sponsors/viam-light.svg">
    <img src="docs/sponsors/viam-light.svg" alt="Viam logo" width="180">
  </picture>
</a>

**What they do:** Software for connecting hardware, collecting machine data, and developing, deploying and managing robotics applications.

**Event contribution:** Robot-arm kits and mentors.

**How we use it in the project:**

Connect to the hackathon machine and inspect its configured arms and grippers:

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-viam.txt
# Set VIAM_MACHINE_ADDRESS, VIAM_API_KEY and VIAM_API_KEY_ID in .env.
venv/bin/python -m viam_integration --list
venv/bin/python -m viam_integration
```

Use the **hostname from the machine's CONNECT tab** (ending in `.viam.cloud`),
not its machine ID or machine-part ID. The CLI loads the repository's `.env`;
existing shell environment variables take precedence.

Reusable connection and inspection logic lives in `viam_integration` (exports
`connect` and `inspect_machine`). Importing it does not load environment files;
only the CLI does. Run it with `python -m viam_integration`.
Keep credential values in the ignored local `.env` file, never in source code.

`--list` verifies authentication/connectivity and lists configured resources.
The default command also reads arm joint positions and gripper movement status;
it does not command movement. Components are discovered automatically, and each
hardware failure is reported separately with a nonzero exit status. A servo
`sync_read` or serial `input/output error` after connecting is a machine-side
hardware issue: check the affected arm's power, USB/serial connection and Viam
component configuration.

For the same machine's two live camera feeds, use the
[pi-arm4 dual-camera viewer](pi-arm4-camera/README.md). The capture server runs
on the Pi; the authenticated Viam CLI tunnel runs on your computer:

```bash
# From the repository root, after starting the camera server on the Pi:
bash pi-arm4-camera/tunnel.sh
# Open http://localhost:8766
```

The Python inspection CLI uses the API key settings above. The camera tunnel
uses your separately authenticated Viam CLI session. Installing
`requirements-viam.txt` does not install the Viam CLI or FFmpeg; the viewer's
setup guide lists those requirements. Both workflows are read-only with respect
to arm movement.

### Vonage

<a href="https://www.vonage.com/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/sponsors/vonage-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/sponsors/vonage-light.svg">
    <img src="docs/sponsors/vonage-light.svg" alt="Vonage logo" width="180">
  </picture>
</a>

**What they do:** Communications APIs for voice, video, messaging and identity verification, plus business communications and contact-center products.

**Event contribution:** Food, API credits and the Demo Day venue.

**How we use it in the project:**

<!-- Reserved for the team's Vonage integration details. -->

### Tavily

<a href="https://www.tavily.com/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/sponsors/tavily-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/sponsors/tavily-light.svg">
    <img src="docs/sponsors/tavily-light.svg" alt="Tavily logo" width="180">
  </picture>
</a>

**What they do:** APIs for AI agents to search the web, extract content, crawl websites and conduct research.

**Event contribution:** Search API credits.

**How we use it in the project:**

<!-- Reserved for the team's Tavily integration details. -->

### Sources

- [Official hackathon page](https://luma.com/onzzmytl)
- [Demo Day registration](https://luma.com/3perce-pi2u)
- [Viam](https://www.viam.com/)
- [Vonage](https://www.vonage.com/)
- [Tavily](https://www.tavily.com/)

Sponsor logos are reproduced from the sponsors' official websites for identification; their trademarks remain with their respective owners.

## Author garden spaces with OpenCode

Connect OpenCode to the local Open-Industries MCP server and use `/author-space`
to generate, validate, save and export conceptual garden layouts. Setup, the
committed sample, and a model-free MCP replay are in
[OpenCode space authoring](docs/opencode-authoring.md).
