from otoe import HStack, Panel, Text, VStack, component


@component
def MissionCard(*, mission):
    return Panel(
        VStack(
            HStack(
                Text(mission["vector"], className="mission-vector"),
                Text(f"OPSEC {mission['opsec']}", className="mission-opsec"),
                className="mission-meta",
            ),
            Text(mission["name"], className="mission-title"),
            Text(mission["description"], className="mission-description"),
            className="mission-card-body",
        ),
        className="mission-card",
    )

