MISSION = {
    "id": "handshake_hunter",
    "name": "Handshake Hunter",
    "description": (
        "Passive capture of WPA/WPA2 4-way handshakes against a scoped AP. "
        "No deauth, no injection; client-driven reassociation only."
    ),
    "vector": "WIFI",
    "opsec": "HIGH",
    "validation": "IMPLEMENTED",
    "profile": "Stealth / Passive / 300s",
    "scope": "DEMO-SCOPE-001 (demo-lab)",
    "target": "DEMO-GUEST (02:00:5e:00:53:01)",
    "asset": "demo-radio-0",
    "posture": "STEALTH / CHAMELEON",
}

LOG_LINES = [
    {"id": "l01", "ts": "08:49:58", "lvl": "info", "msg": "wraith.daemon: attach interface wlan1mon"},
    {"id": "l02", "ts": "08:49:58", "lvl": "ok", "msg": "wraith.daemon: monitor mode confirmed"},
    {"id": "l03", "ts": "08:49:59", "lvl": "cmd", "msg": "> handshake_hunter --scope DEMO-SCOPE-001 --target 02:00:5e:00:53:01 --window 300s --stealth"},
    {"id": "l04", "ts": "08:50:00", "lvl": "sig", "msg": "policy_guard: scope check OK - target in DEMO-SCOPE-001"},
    {"id": "l05", "ts": "08:50:00", "lvl": "sig", "msg": "policy_guard: posture=STEALTH - deauth/injection DISABLED"},
    {"id": "l06", "ts": "08:50:01", "lvl": "info", "msg": "chameleon: MAC rotated to 02:00:5e:00:53:10"},
    {"id": "l07", "ts": "08:50:02", "lvl": "info", "msg": "channel lock: 11 @ 2.462GHz"},
    {"id": "l08", "ts": "08:50:02", "lvl": "info", "msg": "listening for EAPOL frames ... window=300s"},
    {"id": "l09", "ts": "08:50:19", "lvl": "info", "msg": "client 02:00:5e:00:53:7e associated with 02:00:5e:00:53:01"},
    {"id": "l10", "ts": "08:50:20", "lvl": "info", "msg": "EAPOL M1 observed (AP -> STA)"},
    {"id": "l11", "ts": "08:50:20", "lvl": "info", "msg": "EAPOL M2 observed (STA -> AP)"},
    {"id": "l12", "ts": "08:50:21", "lvl": "ok", "msg": "EAPOL M4 observed - 4-way handshake complete"},
    {"id": "l13", "ts": "08:50:21", "lvl": "sig", "msg": "HANDSHAKE CAPTURED / frames=4 / quality=CLEAN"},
    {"id": "l14", "ts": "08:50:22", "lvl": "info", "msg": "evidence: hs_demo_0001_20260422T085022Z.pcapng - 14.3 KB"},
    {"id": "l15", "ts": "08:50:23", "lvl": "ok", "msg": "loot.ingest: 1 handshake -> loot/wifi/handshakes/DEMO-GUEST"},
    {"id": "l16", "ts": "08:51:04", "lvl": "warn", "msg": "beacon anomaly: RSSI delta -18dBm (possible client roam)"},
    {"id": "l17", "ts": "08:51:12", "lvl": "sig", "msg": "finding: WPA2 handshake captured - escalated to workbench queue"},
]

EVENTS = [
    {"id": "e01", "ts": "08:50:00", "tag": "SCOPE", "sev": "ok", "msg": "Policy guard approved DEMO-SCOPE-001"},
    {"id": "e02", "ts": "08:50:01", "tag": "CHAMELEON", "sev": "ok", "msg": "MAC rotation confirmed"},
    {"id": "e03", "ts": "08:50:02", "tag": "RADIO", "sev": "ok", "msg": "Monitor mode on wlan1mon / ch11"},
    {"id": "e04", "ts": "08:50:20", "tag": "EAPOL", "sev": "ok", "msg": "4-way handshake progression 1-4"},
    {"id": "e05", "ts": "08:50:21", "tag": "CAPTURE", "sev": "ok", "msg": "Handshake sealed to vault"},
    {"id": "e06", "ts": "08:51:04", "tag": "RADIO", "sev": "warn", "msg": "RSSI delta - possible client roam"},
    {"id": "e07", "ts": "08:51:12", "tag": "FINDING", "sev": "warn", "msg": "Escalated to workbench queue"},
]

STREAM_LINES = [
    {"lvl": "info", "msg": "beacon: DEMO-GUEST (02:00:...:01) / rssi -62dBm"},
    {"lvl": "info", "msg": "probe_req: 02:00:...:7e seeking DemoOffice"},
    {"lvl": "ok", "msg": "channel hop confirmed / 11 -> 11 locked"},
    {"lvl": "warn", "msg": "retry storm observed / 3.2% window average"},
    {"lvl": "sig", "msg": "chameleon: MAC cadence check OK"},
]
