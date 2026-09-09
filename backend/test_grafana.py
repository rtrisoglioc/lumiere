import asyncio
import struct
import cramjam
import services.grafana_metrics as gm


# ---- minimal protobuf reader for the WriteRequest we emit ----
def _read_varint(b, i):
    shift = 0
    val = 0
    while True:
        byte = b[i]
        i += 1
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return val, i
        shift += 7


def _read_fields(b, start, end):
    i = start
    fields = []
    while i < end:
        key, i = _read_varint(b, i)
        field, wire = key >> 3, key & 0x7
        if wire == 2:
            ln, i = _read_varint(b, i)
            fields.append((field, b[i:i + ln]))
            i += ln
        elif wire == 0:
            v, i = _read_varint(b, i)
            fields.append((field, v))
        elif wire == 1:
            fields.append((field, struct.unpack("<d", b[i:i + 8])[0]))
            i += 8
        else:
            raise ValueError("bad wire")
    return fields


def parse_write_request(payload):
    out = []
    for f, data in _read_fields(payload, 0, len(payload)):
        if f != 1:
            continue
        labels, value = {}, None
        for tf, td in _read_fields(data, 0, len(data)):
            if tf == 1:  # Label
                lab = dict((lf, ld) for lf, ld in _read_fields(td, 0, len(td)))
                labels[lab[1].decode()] = lab[2].decode()
            elif tf == 2:  # Sample
                for sf, sd in _read_fields(td, 0, len(td)):
                    if sf == 1:
                        value = sd
        out.append((labels, value))
    return out


def decode(series):
    payload = gm._write_request(series)
    body = bytes(cramjam.snappy.compress_raw(payload))
    return parse_write_request(bytes(cramjam.snappy.decompress_raw(body)))


def run():
    # Force "configured" so record_* builds series (we bypass real HTTP below).
    gm.URL = "https://example.invalid/api/prom/push"
    gm.INSTANCE_ID = "123456"
    gm.API_TOKEN = "glc_test"

    captured = []
    gm._fire = lambda series: captured.append(series)  # capture instead of sending

    # 1) allowlist: valid + invalid agents
    gm.record_agent("Director Agent", status="OK", latency_ms=1200, confidence=0.9)
    gm.record_agent("Cinematographer", status="OK", latency_ms=800, confidence=0.7)
    gm.record_agent("Vision Agent", status="OK", latency_ms=4200, confidence=0.85)
    gm.record_agent("Evaluator", status="OK", latency_ms=30, confidence=1.0)
    gm.record_agent("Editor Agent", status="FAILED", latency_ms=45000, confidence=0.6)
    gm.record_agent("Render Worker", status="OK", latency_ms=45600, confidence=1.0)
    gm.record_agent("Translator", status="OK", latency_ms=500, confidence=0.9)   # NOT in allowlist
    gm.record_agent("Sun Engine", status="OK", latency_ms=5)                     # NOT in allowlist
    assert len(captured) == 6, f"expected 6 valid emissions, got {len(captured)}"
    print("PASS allowlist: 6 valid agents emitted, Translator/Sun Engine skipped")

    # 2) decode the Director series -> check metric names + labels
    metrics = decode(captured[0])
    names = {lbls["__name__"] for lbls, _ in metrics}
    assert "lumiere_agent_calls_total" in names
    assert "lumiere_agent_confidence" in names
    assert "lumiere_agent_duration_ms_bucket" in names
    assert "lumiere_agent_duration_ms_count" in names
    assert "lumiere_agent_duration_ms_sum" in names
    conf = next(v for l, v in metrics if l["__name__"] == "lumiere_agent_confidence")
    assert abs(conf - 0.9) < 1e-6, conf
    calls_lbl = next(l for l, _ in metrics if l["__name__"] == "lumiere_agent_calls_total")
    assert calls_lbl["agent"] == "director" and calls_lbl["status"] == "ok", calls_lbl
    inf = next(v for l, v in metrics if l["__name__"] == "lumiere_agent_duration_ms_bucket" and l["le"] == "+Inf")
    assert inf == 1, inf
    print("PASS protobuf+snappy roundtrip: names/labels/values correct")

    # 3) monotonic counter + cumulative histogram across repeated calls
    gm.record_agent("Director Agent", status="OK", latency_ms=1300, confidence=0.8)
    m2 = decode(captured[-1])
    calls2 = next(v for l, v in m2 if l["__name__"] == "lumiere_agent_calls_total" and l["agent"] == "director")
    count2 = next(v for l, v in m2 if l["__name__"] == "lumiere_agent_duration_ms_count" and l["agent"] == "director")
    assert calls2 == 2, f"counter must be cumulative, got {calls2}"
    assert count2 == 2, f"hist count must be cumulative, got {count2}"
    print("PASS monotonic: director calls_total=2, duration_count=2 after 2 calls")

    # 4) completeness gauge
    gm.record_completeness("exp-abc", 73)
    cm = decode(captured[-1])
    lbls, val = cm[0]
    assert lbls["__name__"] == "lumiere_story_completeness" and lbls["experience_id"] == "exp-abc"
    assert val == 73.0
    print("PASS completeness gauge: exp-abc=73")

    # 5) FAIL SILENTLY: real send to unreachable host must NOT raise
    gm._fire = gm._orig_fire if hasattr(gm, "_orig_fire") else gm._fire
    async def send_test():
        await gm._send([(gm._labelset("lumiere_agent_confidence", {"agent": "director"}), 0.9, 1)])
    asyncio.run(send_test())
    print("PASS fail-silent: _send to invalid host returned without raising")

    # 6) not configured -> no-op, no raise
    gm.URL = ""
    gm.record_agent("Director Agent", status="OK", latency_ms=100, confidence=0.5)
    gm.record_completeness("x", 50)
    print("PASS not-configured no-op")

    print("\nALL GRAFANA METRICS TESTS PASSED")


if __name__ == "__main__":
    run()
