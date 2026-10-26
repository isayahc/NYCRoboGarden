"""Refresh the self-contained garden map from official NYC Open Data sources."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {'gardens': 'p78i-pat6', 'boroughs': 'gthc-hcne'}
BOROUGHS = {'B': 'Brooklyn', 'X': 'Bronx', 'M': 'Manhattan', 'Q': 'Queens', 'R': 'Staten Island'}


def fetch_rows(dataset, order):
    rows = []
    while True:
        query = urlencode({'$limit': 1000, '$offset': len(rows), '$order': order})
        with urlopen(f'https://data.cityofnewyork.us/resource/{dataset}.json?{query}', timeout=60) as response:
            page = json.load(response)
        if not isinstance(page, list):
            raise ValueError('Expected Socrata record array')
        rows.extend(page)
        if len(page) < 1000:
            return rows


def project(point):
    lon, lat = point[:2]
    return (lon*111320*math.cos(math.radians(40.7)), lat*111320)


def simplify_line(points, tolerance=20):
    """Iterative Douglas–Peucker in approximate local meters, for display only."""
    if len(points) < 3:
        return points
    xy = [project(point) for point in points]
    keep = {0, len(points)-1}
    stack = [(0, len(points)-1)]
    while stack:
        first, last = stack.pop()
        ax, ay = xy[first]
        bx, by = xy[last]
        dx, dy = bx-ax, by-ay
        norm = dx*dx+dy*dy
        worst, index = 0, first
        for i in range(first+1, last):
            x, y = xy[i]
            t = max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/norm)) if norm else 0
            distance = (x-ax-t*dx)**2+(y-ay-t*dy)**2
            if distance > worst:
                worst, index = distance, i
        if worst > tolerance*tolerance:
            keep.add(index)
            stack.extend(((first, index), (index, last)))
    return [points[i] for i in sorted(keep)]


def simplify_ring(ring):
    # Split closed rings at their farthest point so coincident endpoints do not
    # collapse a coastline. Preserve small island rings if simplification collapses them.
    if len(ring) < 5:
        return ring
    x, y = project(ring[0])
    split = max(range(1, len(ring)-1), key=lambda i: (project(ring[i])[0]-x)**2+(project(ring[i])[1]-y)**2)
    result = simplify_line(ring[:split+1])[:-1] + simplify_line(ring[split:])
    return result if len(result) >= 4 else ring


def geometry(source, simplified=False):
    if not source or source.get('type') not in ('Polygon', 'MultiPolygon'):
        return None
    polygons = source['coordinates'] if source['type'] == 'MultiPolygon' else [source['coordinates']]
    return {'type': 'MultiPolygon', 'coordinates': [
        [[[round(float(v), 6) for v in p[:2]] for p in (simplify_ring(ring) if simplified else ring)]
         for ring in polygon] for polygon in polygons]}


def build(gardens, boroughs):
    sites = []
    for row in gardens:
        try:
            lat, lon = float(row['lat']), float(row['lon'])
            location = [lon, lat] if 40 < lat < 41.1 and -74.4 < lon < -73.6 else None
        except (KeyError, TypeError, ValueError):
            location = None
        sites.append({'id': row.get('parksid', ''), 'name': row.get('gardenname', 'Unnamed garden'),
                      'address': row.get('address', ''), 'borough': BOROUGHS.get(row.get('borough'), row.get('borough', 'Unknown')),
                      'status': row.get('status', 'Unknown'), 'location': location,
                      'footprint': geometry(row.get('multipolygon'))})
    boundaries = [{'name': row['boroname'], 'geometry': geometry(row['the_geom'], simplified=True)} for row in boroughs]
    if {row['name'] for row in boundaries} != set(BOROUGHS.values()):
        raise ValueError('Expected official boundaries for all five boroughs')
    return {'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'sources': {key: f'https://data.cityofnewyork.us/d/{value}' for key, value in SOURCES.items()},
            'crs': 'EPSG:4326', 'boundary_simplification_m': 20,
            'record_count': len(sites), 'mapped_count': sum(s['location'] is not None for s in sites),
            'gardens': sites, 'boroughs': boundaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/gardens-map/map-data.json')
    args = parser.parse_args()
    result = build(fetch_rows(SOURCES['gardens'], 'parksid'), fetch_rows(SOURCES['boroughs'], 'borocode'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, separators=(',', ':'), ensure_ascii=False)+'\n')
    temporary.replace(args.output)
    print(f'{result["record_count"]} records, {result["mapped_count"]} mapped, {len(result["boroughs"])} boroughs; {args.output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
