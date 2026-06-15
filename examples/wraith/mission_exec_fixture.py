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
    {"id": "l01", "ts": "08:49:58", "level": "info", "message": "wraith.daemon: attach interface wlan1mon"},
    {"id": "l02", "ts": "08:49:58", "level": "ok", "message": "wraith.daemon: monitor mode confirmed"},
    {"id": "l03", "ts": "08:49:59", "level": "cmd", "message": "> handshake_hunter --scope DEMO-SCOPE-001 --target 02:00:5e:00:53:01 --window 300s --stealth"},
    {"id": "l04", "ts": "08:50:00", "level": "sig", "message": "policy_guard: scope check OK - target in DEMO-SCOPE-001"},
    {"id": "l05", "ts": "08:50:00", "level": "sig", "message": "policy_guard: posture=STEALTH - deauth/injection DISABLED"},
    {"id": "l06", "ts": "08:50:01", "level": "info", "message": "chameleon: MAC rotated to 02:00:5e:00:53:10"},
    {"id": "l07", "ts": "08:50:02", "level": "info", "message": "channel lock: 11 @ 2.462GHz"},
    {"id": "l08", "ts": "08:50:02", "level": "info", "message": "listening for EAPOL frames ... window=300s"},
    {"id": "l09", "ts": "08:50:19", "level": "info", "message": "client 02:00:5e:00:53:7e associated with 02:00:5e:00:53:01"},
    {"id": "l10", "ts": "08:50:20", "level": "info", "message": "EAPOL M1 observed (AP -> STA)"},
    {"id": "l11", "ts": "08:50:20", "level": "info", "message": "EAPOL M2 observed (STA -> AP)"},
    {"id": "l12", "ts": "08:50:21", "level": "ok", "message": "EAPOL M4 observed - 4-way handshake complete"},
    {"id": "l13", "ts": "08:50:21", "level": "sig", "message": "HANDSHAKE CAPTURED / frames=4 / quality=CLEAN"},
    {"id": "l14", "ts": "08:50:22", "level": "info", "message": "evidence: hs_demo_0001_20260422T085022Z.pcapng - 14.3 KB"},
    {"id": "l15", "ts": "08:50:23", "level": "ok", "message": "loot.ingest: 1 handshake -> loot/wifi/handshakes/DEMO-GUEST"},
    {"id": "l16", "ts": "08:51:04", "level": "warn", "message": "beacon anomaly: RSSI delta -18dBm (possible client roam)"},
    {"id": "l17", "ts": "08:51:12", "level": "sig", "message": "finding: WPA2 handshake captured - escalated to workbench queue"},
]

EVENTS = [
    {"id": "e01", "ts": "08:50:00", "tag": "SCOPE", "severity": "ok", "message": "Policy guard approved DEMO-SCOPE-001"},
    {"id": "e02", "ts": "08:50:01", "tag": "CHAMELEON", "severity": "ok", "message": "MAC rotation confirmed"},
    {"id": "e03", "ts": "08:50:02", "tag": "RADIO", "severity": "ok", "message": "Monitor mode on wlan1mon / ch11"},
    {"id": "e04", "ts": "08:50:20", "tag": "EAPOL", "severity": "ok", "message": "4-way handshake progression 1-4"},
    {"id": "e05", "ts": "08:50:21", "tag": "CAPTURE", "severity": "ok", "message": "Handshake sealed to vault"},
    {"id": "e06", "ts": "08:51:04", "tag": "RADIO", "severity": "warn", "message": "RSSI delta - possible client roam"},
    {"id": "e07", "ts": "08:51:12", "tag": "FINDING", "severity": "warn", "message": "Escalated to workbench queue"},
]

STREAM_LINES = [
    {"level": "info", "message": "beacon: DEMO-GUEST (02:00:...:01) / rssi -62dBm"},
    {"level": "info", "message": "probe_req: 02:00:...:7e seeking DemoOffice"},
    {"level": "ok", "message": "channel hop confirmed / 11 -> 11 locked"},
    {"level": "warn", "message": "retry storm observed / 3.2% window average"},
    {"level": "sig", "message": "chameleon: MAC cadence check OK"},
]
