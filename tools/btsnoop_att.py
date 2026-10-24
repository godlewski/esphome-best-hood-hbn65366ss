"""Print ATT traffic from a btsnoop log: handle->UUID map, then writes/notifications/reads with times."""
import datetime
import struct
import sys

EPOCH_DELTA = 0x00DCDDB30F2F8000  # btsnoop microseconds (year 0) -> unix epoch


def records(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"btsnoop\0", "not a btsnoop file"
    off = 16
    while off + 24 <= len(data):
        _olen, ilen, flags, _drops, ts = struct.unpack(">IIIIq", data[off : off + 24])
        off += 24
        yield ts, flags, data[off : off + ilen]
        off += ilen


def uuid_str(b):
    if len(b) == 2:
        return "%04x" % struct.unpack("<H", b)[0]
    return b[::-1].hex()


def main(path):
    handles = {}  # value handle -> uuid
    frags = {}  # (conn, direction) -> partial l2cap
    events = []
    for ts, flags, pkt in records(path):
        if not pkt or pkt[0] != 0x02:
            continue
        sent = (flags & 1) == 0  # 0 = host->controller
        hdr, _alen = struct.unpack("<HH", pkt[1:5])
        conn, pb = hdr & 0x0FFF, (hdr >> 12) & 0x3
        payload = pkt[5:]
        key = (conn, sent)
        if pb == 0x1 and key in frags:
            frags[key] += payload
        else:
            frags[key] = payload
        buf = frags[key]
        if len(buf) < 4:
            continue
        llen, cid = struct.unpack("<HH", buf[:4])
        if len(buf) - 4 < llen:
            continue
        del frags[key]
        if cid != 0x0004:
            continue
        att = buf[4 : 4 + llen]
        op = att[0]
        t = datetime.datetime.fromtimestamp((ts - EPOCH_DELTA) / 1e6).strftime("%H:%M:%S.%f")[:-3]
        if op == 0x09:  # read by type rsp (characteristic declarations)
            ln = att[1]
            for i in range(2, len(att), ln):
                e = att[i : i + ln]
                if len(e) >= 7:
                    vh = struct.unpack("<H", e[3:5])[0]
                    handles[vh] = uuid_str(e[5:])
        events.append((t, sent, conn, op, att))
    names = {0x12: "WRITE_REQ", 0x52: "WRITE_CMD", 0x1B: "NOTIFY", 0x1D: "INDICATE", 0x0A: "READ_REQ",
             0x0B: "READ_RSP", 0x13: "WRITE_RSP", 0x01: "ERROR"}
    print("# handle map")
    for h in sorted(handles):
        print("0x%04x %s" % (h, handles[h]))
    print("# events")
    last_read = None
    for t, sent, conn, op, att in events:
        d = "->" if sent else "<-"
        if op in (0x12, 0x52, 0x1B, 0x1D, 0x0A):
            h = struct.unpack("<H", att[1:3])[0]
            if op == 0x0A:
                last_read = h
            u = handles.get(h, "?")
            short = u[:8] if len(u) > 8 else u
            val = att[3:].hex()
            print(f"{t} {d} {names[op]:9} h=0x{h:04x} {short} {val}")
        elif op == 0x0B:
            u = handles.get(last_read, "?") if last_read else "?"
            print(f"{t} {d} READ_RSP  h=0x{last_read or 0:04x} {u[:8]} {att[1:].hex()}")
        elif op == 0x01:
            print(f"{t} {d} ERROR     {att[1:].hex()}")


if __name__ == "__main__":
    main(sys.argv[1])
