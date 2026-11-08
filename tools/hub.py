#!/usr/bin/env python3
"""Find an exact shortest hub visit order with precedence constraints.

Usage: python3 tools/hub.py plan.json
Use - or omit the path to read JSON from stdin. Output is JSON on stdout.

Version 1 input (all positions use one shared coordinate system):
  {"version": 1, "start": [0, 0], "end": [10, 0],
   "axis_scale": [1, 1],
   "stops": [{"id": "a", "position": [1, 2]},
             {"id": "b", "position": [3, 4]}],
   "before": [["a", "b"]]}

Every stop is visited once. Use separate IDs for required return visits.
end is optional/null: omit it for a free finish; use start for a round trip.
It is the onward destination, not a required final stop. Its final leg counts
in the objective. before lists genuine prerequisites between stop IDs.
axis_scale defaults to [1, 1]; distance is hypot(dx * sx, dy * sy). For map
percentages, verified map width/100 and height/100 give distance in yards;
unscaled percentages give coordinate units. Walls and ramps are not modeled.

Subset dynamic programming uses O(n^2 * 2^n) time and O(n * 2^n) memory.
Hard limits: 16 stops (excluding start/end), 1 second of cooperative solver
wall time, and 256 KiB of JSON input. --seconds can lower the time budget.
Equal-cost ties are deterministic; optimality is within floating-point
Euclidean arithmetic. Optional visits and game-state inference are outside
this tool: the author supplies applicable visits and verified constraints.

Exit codes: 0 optimal, 2 invalid_input, 3 limit_exceeded. Limits never return
an order claiming optimality. The Python API raises InputError/LimitExceeded.
"""
import argparse
from array import array
import json
from math import hypot, inf, isfinite
from pathlib import Path
import sys
from time import perf_counter

MAX_STOPS = 16
MAX_SECONDS = 1.0
MAX_INPUT_BYTES = 256 * 1024


class InputError(ValueError):
    """The supplied model is invalid."""


class LimitExceeded(RuntimeError):
    """A hard resource limit prevents an exact result."""


def point(value, name, positive=False):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InputError(f'{name} must contain two finite numbers.')
    result = []
    for number in value:
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise InputError(f'{name} must contain two finite numbers.')
        try:
            number = float(number)
        except OverflowError:
            raise InputError(f'{name} contains an out-of-range number.') from None
        if not isfinite(number) or (positive and number <= 0):
            raise InputError(f'{name} must contain finite {"positive " if positive else ""}numbers.')
        result.append(number)
    return tuple(result)


def validate(problem):
    if not isinstance(problem, dict):
        raise InputError('The input must be a JSON object.')
    allowed = {'version', 'start', 'end', 'axis_scale', 'stops', 'before'}
    if set(problem) - allowed:
        raise InputError('Unknown input field; see --help for the version 1 format.')
    if type(problem.get('version')) is not int or problem['version'] != 1:
        raise InputError('version must be 1.')
    start = point(problem.get('start'), 'start')
    end = point(problem['end'], 'end') if problem.get('end') is not None else None
    scale = point(problem.get('axis_scale', [1, 1]), 'axis_scale', positive=True)
    stops = problem.get('stops')
    if not isinstance(stops, list):
        raise InputError('stops must be an array.')
    if len(stops) > MAX_STOPS:
        raise LimitExceeded(f'At most {MAX_STOPS} required stops are supported.')
    positions = {}
    for stop in stops:
        if not isinstance(stop, dict) or set(stop) != {'id', 'position'}:
            raise InputError('Each stop must contain exactly id and position.')
        key = stop['id']
        if not isinstance(key, str) or not key.strip() or key in positions:
            raise InputError('Stop IDs must be unique nonempty strings.')
        positions[key] = point(stop['position'], f'Position of {key}')
    ids = sorted(positions)
    indices = {key: i for i, key in enumerate(ids)}
    before = problem.get('before', [])
    if not isinstance(before, list):
        raise InputError('before must be an array of [earlier, later] ID pairs.')
    prerequisites = [0] * len(ids)
    for pair in before:
        if not isinstance(pair, list) or len(pair) != 2 or any(
            not isinstance(key, str) or key not in indices for key in pair
        ):
            raise InputError('Each before pair must reference two known stop IDs.')
        prerequisites[indices[pair[1]]] |= 1 << indices[pair[0]]
    visited = 0
    for _ in ids:
        eligible = [i for i in range(len(ids))
                    if not visited & (1 << i) and prerequisites[i] & visited == prerequisites[i]]
        if not eligible:
            raise InputError('Ordering constraints contain a cycle.')
        for i in eligible:
            visited |= 1 << i
        if visited == (1 << len(ids)) - 1:
            break
    return ids, [positions[key] for key in ids], start, end, scale, prerequisites


def solve(problem, seconds=MAX_SECONDS):
    """Return an optimal order and total distance, or raise a documented error."""
    begin = perf_counter()
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 < seconds <= MAX_SECONDS:
        raise InputError(f'seconds must be positive and at most {MAX_SECONDS:g}.')
    deadline = begin + seconds

    def check_deadline():
        if perf_counter() >= deadline:
            raise LimitExceeded(f'The {seconds:g}-second solver time budget was exceeded.')

    ids, positions, start, end, scale, prerequisites = validate(problem)

    def distance(a, b):
        value = hypot((a[0] - b[0]) * scale[0], (a[1] - b[1]) * scale[1])
        if not isfinite(value):
            raise InputError('Coordinates or scaling produce a non-finite distance.')
        return value

    n = len(ids)
    if not n:
        best = distance(start, end) if end is not None else 0.0
        order = []
    else:
        distances = [[distance(a, b) for b in positions] for a in positions]
        arrival = [distance(start, p) for p in positions]
        departure = [distance(p, end) if end is not None else 0.0 for p in positions]
        # Also bound accumulated costs, so overflow cannot masquerade as a result.
        largest = max(arrival + departure + [max(row) for row in distances])
        if not isfinite(largest * (n + 1)):
            raise InputError('Coordinates or scaling can overflow the route distance.')
        check_deadline()
        full = (1 << n) - 1
        costs = array('d', [inf]) * (n * (full + 1))
        parents = bytearray([255]) * (n * (full + 1))
        reachable = bytearray(full + 1)
        for j in range(n):
            if not prerequisites[j]:
                costs[(1 << j) * n + j] = arrival[j]
                reachable[1 << j] = 1
        check_deadline()
        for mask in range(1, full):
            if mask & 127 == 0:
                check_deadline()
            if not reachable[mask]:
                continue
            remaining = full ^ mask
            eligible = []
            while remaining:
                bit = remaining & -remaining
                remaining ^= bit
                j = bit.bit_length() - 1
                if prerequisites[j] & mask == prerequisites[j]:
                    eligible.append((j, (mask | bit) * n + j, mask | bit))
            bits = mask
            base = mask * n
            while bits:
                bit = bits & -bits
                bits ^= bit
                i = bit.bit_length() - 1
                old = costs[base + i]
                if old == inf:
                    continue
                row = distances[i]
                for j, target, target_mask in eligible:
                    value = old + row[j]
                    if value < costs[target]:
                        costs[target] = value
                        parents[target] = i
                        reachable[target_mask] = 1
        final = min(range(n), key=lambda j: costs[full * n + j] + departure[j])
        best = costs[full * n + final] + departure[final]
        order = []
        mask, j = full, final
        while mask:
            order.append(ids[j])
            previous = parents[mask * n + j]
            mask ^= 1 << j
            j = previous
        order.reverse()
    check_deadline()
    return {'status': 'optimal', 'order': order, 'distance': best,
            'axis_scale': list(scale), 'elapsed_ms': round((perf_counter() - begin) * 1000, 3)}


def load_problem(stream):
    data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise LimitExceeded(f'JSON input exceeds {MAX_INPUT_BYTES} bytes.')
    try:
        return json.loads(data)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InputError(f'Invalid JSON: {error}') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('plan', nargs='?', default='-', help='Input JSON path, or - for stdin')
    parser.add_argument('--seconds', type=float, default=MAX_SECONDS, help='Lower the 1-second search budget')
    args = parser.parse_args()
    try:
        if args.plan == '-':
            problem = load_problem(sys.stdin.buffer)
        else:
            with Path(args.plan).open('rb') as stream:
                problem = load_problem(stream)
        result = solve(problem, args.seconds)
        code = 0
    except LimitExceeded as error:
        result, code = {'status': 'limit_exceeded', 'message': str(error)}, 3
    except (InputError, OSError) as error:
        result, code = {'status': 'invalid_input', 'message': str(error)}, 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
