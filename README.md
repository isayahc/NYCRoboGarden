# Spooky Civic AI Hackathon

**Project: NYC Robo Garden**

**Selected track: Physical AI for Good**

Built for the [Spooky Civic AI Hackathon: Build Weekend](https://luma.com/onzzmytl), hosted by 3percentclub in NYC and online, October 23–24, 2026, with Demo Day on October 25.

## Problem statement

<!-- Reserved for the team's problem statement. -->

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
