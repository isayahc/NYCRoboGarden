"""Validate and partition manually reviewed, source-backed garden evidence.

Run with ``python3 -m garden_registry.evidence --help``. No network or asset fetches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

CATEGORIES = {'bed', 'growing_area', 'path', 'greenhouse', 'building', 'water',
              'power', 'crop', 'seasonal_product'}


def require(condition: bool, message: str) -> None:
    """Reject an invalid contract value with a readable error."""
    if not condition:
        raise ValueError(message)


def nonempty(value: Any) -> bool:
    """Return whether a value is nonblank text."""
    return isinstance(value, str) and bool(value.strip())


def check_date(value: Any, nullable: bool = True) -> None:
    """Validate a calendar date; unknown dates must be explicit nulls."""
    if value is None and nullable:
        return
    require(isinstance(value, str) and len(value) == 10, 'Expected YYYY-MM-DD')
    date.fromisoformat(value)


def validate(bundle: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Check evidence and return accepted, unresolved and unknown partitions.

    Validation establishes traceability, not factual truth. Humans must verify
    citations, site matches and rights before preparing this input.
    """
    require(bundle['schema_version'] == '1.0', 'Unsupported evidence schema')
    gardens = {row['id'] for row in registry['records']}
    sources: dict[str, Any] = {}
    for source in bundle['sources']:
        require(nonempty(source['id']) and source['id'] not in sources, 'Duplicate/empty source ID')
        for field in ('url', 'publisher', 'title'):
            require(nonempty(source[field]), f'Missing source {field}')
        require(source['url'].startswith(('https://', 'http://')), 'Expected source web URL')
        check_date(source['retrieved_at'], False)
        check_date(source['published_at'])
        rights = source['rights']
        require(rights['status'] in {'unknown', 'licensed', 'permission', 'owned'}, 'Invalid rights status')
        # v1 imports references and paraphrases only, never imagery or plans.
        require(rights['asset_use'] == 'link_only', 'v1 supports link-only sources')
        require(rights['license_url'] is None or nonempty(rights['license_url']), 'Invalid license reference')
        if rights['status'] != 'unknown':
            require(nonempty(rights['license_url']), 'Document the license or permission reference')
        sources[source['id']] = source
    partitions: dict[str, list[dict[str, Any]]] = {'accepted': [], 'unresolved': [], 'unknowns': []}
    ids: set[str] = set()
    for record in bundle['records']:
        rid = record['id']
        require(nonempty(rid) and rid not in ids, 'Duplicate/empty evidence ID')
        ids.add(rid)
        require(record['category'] in CATEGORIES, f'{rid}: invalid category')
        require(record['state'] in {'reported', 'observed', 'planned', 'unknown'}, 'Invalid state')
        check_date(record['observed_at'])
        require(nonempty(record['time_basis']), 'Explain observation time or its absence')
        confidence = record['confidence']
        require(confidence['level'] in {'high', 'medium', 'low', 'unknown'}, 'Invalid confidence')
        require(nonempty(confidence['rationale']), 'Explain confidence')
        require(isinstance(record['limitations'], list) and all(nonempty(x) for x in record['limitations']), 'Invalid limitations')
        match = record['site_match']
        require(match['status'] in {'confirmed', 'ambiguous', 'unmatched'}, 'Invalid site match')
        require(nonempty(match['rationale']), 'Explain site match')
        require(isinstance(match['candidates'], list) and all(x in gardens for x in match['candidates']), 'Unknown candidate garden')
        if match['status'] == 'confirmed':
            require(match['garden_id'] in gardens and match['garden_id'] in match['candidates'], 'Invalid confirmed garden')
        else:
            require(match['garden_id'] is None, 'Unresolved matches cannot have a garden ID')
        require(record['layout'] is None, 'v1 has no verified layout geometry; attach a source reference')
        season = record['season']
        require(season is None or nonempty(season), 'Season must be source-stated text or null')
        require(record['unit'] is None or nonempty(record['unit']), 'Invalid unit')
        citations = record['citations']
        require(isinstance(citations, list), 'Citations must be a list')
        for citation in citations:
            require(citation['source_id'] in sources, 'Dangling source reference')
            require(nonempty(citation['locator']) and nonempty(citation['support']), 'Missing citation support/locator')
        if record['state'] == 'unknown':
            require(all(record[k] is None for k in ('claim', 'value', 'unit', 'observed_at', 'season')), 'Unknowns cannot assert facts')
            require(confidence['level'] == 'unknown', 'Unknown confidence required')
            key = 'unknowns'
        else:
            require(nonempty(record['claim']) and bool(citations), 'Facts require a claim and citations')
            require(confidence['level'] != 'unknown', 'Explain confidence in a factual claim')
            if record['state'] == 'observed':
                require(record['observed_at'] is not None, 'Direct observations require a date')
            key = 'accepted' if match['status'] == 'confirmed' else 'unresolved'
        partitions[key].append(record)
    payload = {'schema_version': '1.0', 'registry_snapshot_version': registry['snapshot_version'],
               'sources': sorted(sources.values(), key=lambda x: x['id']),
               **{key: sorted(rows, key=lambda x: x['id']) for key, rows in partitions.items()}}
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'version': hashlib.sha256(canonical.encode()).hexdigest(), **payload}


def main() -> None:
    """Validate a research bundle against a pinned local registry snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.input.read_text()), json.loads(args.registry.read_text()))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'Invalid evidence: {error}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f"Accepted {len(result['accepted'])}; unresolved {len(result['unresolved'])}; unknown {len(result['unknowns'])}")


if __name__ == '__main__':
    main()
