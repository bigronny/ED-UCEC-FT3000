# Simulated WinWing UFC with dials, and a button box (16 buttons, a hat, one axis; reports not numbered).
# $UFC_CMDS lines: press NAME | pulse NAME | hold NAME SECONDS | dial OFFSET VALUE (the UFC);
#                  box press N | box pulse N | box hat V (15: centred) | box axis V (0-4095) (the box)
# $FAKEHID_BOX=0: no box; $FAKEHID_NODESC=1: the box won't give its report descriptor (learned from what changes).
import os, time
B = ["IP", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "0", "Ent", "Opt1", "Opt2", "Opt3", "Opt4", "Opt5",
     "EmCon", "AP", "IFF", "TCN", "ILS", "DL", "BCN", "ON_OFF", "COMM1_CCW", "COMM1_CW", "COMM1_PULL",
     "COMM2_CCW", "COMM2_CW", "COMM2_PULL"]
DIALS = {5: 2000, 7: 2000, 9: 2000}   # each dial in the middle to start with
HELD = {}
BOX = {"hat": 15, "axis": 2048}
BOX_DESC = [0x05, 0x01, 0x09, 0x04, 0xA1, 0x01,                     # a joystick:
            0x05, 0x09, 0x19, 0x01, 0x29, 0x10, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x10, 0x81, 0x02,   # 16 buttons
            0x05, 0x01, 0x09, 0x39, 0x15, 0x00, 0x25, 0x07, 0x75, 0x04, 0x95, 0x01, 0x81, 0x42,   # a hat (0-7, 8+ centred)
            0x75, 0x04, 0x95, 0x01, 0x81, 0x03,                     # padding
            0x09, 0x30, 0x15, 0x00, 0x26, 0xFF, 0x0F, 0x75, 0x10, 0x95, 0x01, 0x81, 0x02,   # X: 0-4095 in 16 bits
            0xC0]


def rep(*names):
    r = [1] + [0] * 63
    for n in list(names) + [h for h, t in HELD.items() if t > time.time() and not h.startswith("box:")]:
        i = B.index(n); r[1 + i // 8] |= 1 << (i % 8)
    for off, v in DIALS.items(): r[off], r[off + 1] = v & 255, v >> 8
    return r


def box_rep(*buttons):
    held = [int(h[4:]) for h, t in HELD.items() if t > time.time() and h.startswith("box:")]
    bits = 0
    for n in list(buttons) + held:
        bits |= 1 << (n - 1)
    return [bits & 255, bits >> 8, BOX["hat"] & 15, BOX["axis"] & 255, BOX["axis"] >> 8]


def enumerate():
    out = [{"product_string": "WINWING UFC1", "vendor_id": 1, "product_id": 2, "path": b"sim"}]
    if os.environ.get("FAKEHID_BOX", "1") != "0":
        out.append({"product_string": "SIM BUTTON BOX", "vendor_id": 0x1234, "product_id": 0xABCD, "path": b"box",
                    "usage_page": 1, "usage": 4})
        out.append({"product_string": "SIM KEYBOARD", "vendor_id": 0x1234, "product_id": 0x1111, "path": b"kbd",
                    "usage_page": 1, "usage": 6})   # (not a game controller: never opened)
    return out


class device:
    def open(self, v, p): self._go(b"sim" if v == 1 else b"box")
    def open_path(self, path): self._go(path)

    def _go(self, path):
        if path not in (b"sim", b"box"):
            raise OSError("not a game controller")
        self.kind, self.pos, self.q = path, 0, []
        if os.path.exists(os.environ["UFC_CMDS"]):   # (only what's sent after it opened)
            self.pos = os.path.getsize(os.environ["UFC_CMDS"])

    def set_nonblocking(self, on): pass
    def close(self): pass

    def get_report_descriptor(self, max_length=4096):
        if self.kind == b"box" and os.environ.get("FAKEHID_NODESC") != "1":
            return list(BOX_DESC)
        raise OSError("not supported")

    def read(self, n):
        path = os.environ["UFC_CMDS"]
        if os.path.exists(path):
            with open(path) as f:
                f.seek(self.pos); new = f.read(); self.pos = f.tell()
            for line in new.splitlines():
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == "box":
                    if self.kind != b"box":
                        continue
                    if parts[1] == "press": self.q += [box_rep(int(parts[2]))] * 3 + [box_rep()] * 2
                    elif parts[1] == "pulse": self.q += [box_rep(int(parts[2])), box_rep()]
                    elif parts[1] == "hold": HELD["box:" + parts[2]] = time.time() + float(parts[3])
                    elif parts[1] == "hat": BOX["hat"] = int(parts[2]); self.q.append(box_rep())
                    elif parts[1] == "axis": BOX["axis"] = int(parts[2]); self.q.append(box_rep())
                    continue
                if self.kind != b"sim":
                    continue
                if parts[0] == "dial": DIALS[int(parts[1])] = int(parts[2]); self.q.append(rep())
                elif parts[0] == "hold": HELD[parts[1]] = time.time() + float(parts[2])
                elif parts[0] == "press": self.q += [rep(parts[1])] * 3 + [rep()] * 2
                else: self.q += [rep(parts[1]), rep()]
        if self.q:
            return self.q.pop(0)
        return rep() if self.kind == b"sim" else box_rep()
