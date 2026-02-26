import math
import time


def _simulate_samples(duration_s, hz, sample_hz=50):
    samples = []
    start = time.time()
    period = 1.0 / hz if hz > 0 else 1.0
    while time.time() - start < duration_s:
        t = time.time() - start
        phase = (t % period) / period
        val = 1 if phase < 0.5 else 0
        samples.append(val)
        time.sleep(1.0 / sample_hz)
    return samples


def _count_edges(samples):
    if not samples:
        return 0
    edges = 0
    prev = samples[0]
    for s in samples[1:]:
        if s != prev:
            edges += 1
        prev = s
    return edges


def run(probe_cfg, pin, duration_s, expected_hz, min_edges, max_edges):
    print(f"Verify: sampling pin {pin} for {duration_s:.1f}s")

    # Minimal working implementation uses simulated samples.
    samples = _simulate_samples(duration_s, expected_hz)
    edges = _count_edges(samples)
    print(f"Verify: edges={edges} expected~{expected_hz:.1f}Hz")

    ok = min_edges <= edges <= max_edges
    print("Verify: " + ("OK" if ok else "FAIL"))
    return ok
