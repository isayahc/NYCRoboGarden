#!/usr/bin/env bash
# Connect the local viewer to pi-arm4.
set -euo pipefail
exec viam machine part tunnel --part 5302b0c9-424d-4220-85bd-08108220e07f --local-port 8766 --destination-port 8766
