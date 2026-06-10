from __future__ import annotations

from otoe import (
    Button,
    FocusScope,
    HStack,
    Input,
    Panel,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    component,
    computed,
    css,
    signal,
)


TASK_BOARD_TITLES = ("Runtime bridge", "Input polish", "Docs pass")


def backend_candidate_app():
    query = signal("seed")
    clicked = signal("none")
    shortcuts = signal(0)
    scroll_y = signal(0)

    def noop(*_args):
        return None

    @component
    def CandidateApp():
        return ShortcutScope(
            FocusScope(
                VStack(
                    Input(
                        value=query,
                        autoFocus=True,
                        onChange=lambda next_value: query.set(next_value),
                        onFocus=noop,
                        onBlur=noop,
                        onKeyDown=noop,
                        className="candidate-input",
                    ),
                    HStack(
                        Button(
                            "One",
                            onClick=lambda: clicked.set("one"),
                            onFocus=noop,
                            onBlur=noop,
                            onKeyDown=noop,
                            className="candidate-button",
                        ),
                        Button(
                            "Two",
                            onClick=lambda: clicked.set("two"),
                            onFocus=noop,
                            onBlur=noop,
                            onKeyDown=noop,
                            className="candidate-button",
                        ),
                        className="candidate-toolbar",
                    ),
                    ScrollView(
                        Button("First", onClick=lambda: clicked.set("first")),
                        Button("Second", onClick=lambda: clicked.set("second")),
                        scrollY=scroll_y,
                        onScroll=lambda next_scroll_y: scroll_y.set(next_scroll_y),
                        className="candidate-list",
                    ),
                    Panel(
                        Text("Capability Panel", className="candidate-status"),
                        title="Capabilities",
                        className="candidate-panel",
                    ),
                    Text(
                        computed(lambda: f"Echo {query.value}"),
                        className="candidate-status candidate-truncate",
                    ),
                    Text(
                        computed(lambda: f"Clicked {clicked.value}"),
                        className="candidate-status",
                    ),
                    Text(
                        computed(lambda: f"Shortcuts {shortcuts.value}"),
                        className="candidate-status",
                    ),
                    className="candidate-shell",
                ),
                className="candidate-focus",
            ),
            onKeyDown=lambda _payload: shortcuts.set(shortcuts.value + 1),
        )

    return CandidateApp()


BACKEND_CANDIDATE_STYLES = css(
    """
    .ui-shortcut-scope {
    }
    .ui-focus-scope {
    }
    .candidate-shell {
      width: 220;
      min-width: 200;
      max-width: 260;
      padding: 8;
      gap: 6;
      background: #f8fafc;
      border-style: solid;
      display: flex;
      font-weight: 700;
      margin: 4;
      opacity: 0.96;
    }
    .candidate-focus {
      min-height: 200;
      max-height: 360;
    }
    .candidate-input {
      width: 120;
      border-color: #64748b;
      border-radius: 7;
      border-width: 1;
    }
    .candidate-toolbar {
      width: 200;
      height: 44;
      gap: 4;
      align-items: center;
      justify-content: space-between;
    }
    .candidate-button {
      border-color: #1d4ed8;
      border-radius: 8;
      border-width: 1;
    }
    .candidate-list {
      width: 200;
      height: 44;
      padding: 4;
      gap: 4;
      background: #ffffff;
    }
    .candidate-panel {
      width: 180;
      min-height: 24;
      max-height: 70;
      padding: 3;
      background: #e0f2fe;
      border-color: #0369a1;
      border-radius: 6;
      border-width: 1;
    }
    .candidate-status {
      color: #0f172a;
      font-size: 13;
    }
    .candidate-truncate {
      width: 96;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    """
)
