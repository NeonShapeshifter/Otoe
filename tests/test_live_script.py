import json
import shutil
import subprocess
import textwrap

import pytest

from otoe.live_server import LIVE_SCRIPT


def test_live_script_ignores_stale_event_responses(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("node is not installed")

    script = tmp_path / "live-script-stale-response.js"
    script.write_text(
        textwrap.dedent(
            f"""
            const liveScript = {json.dumps(LIVE_SCRIPT)};

            const listeners = {{}};
            let inputTarget;

            const document = {{
              activeElement: null,
              addEventListener(kind, handler) {{
                listeners[kind] = handler;
              }},
              getElementById(id) {{
                if (id !== "otoe-root") {{
                  throw new Error(`Unexpected element id ${{id}}`);
                }}
                return root;
              }},
            }};

            const root = {{
              innerHTML: "",
              querySelector(selector) {{
                if (selector === "[data-otoe-autofocus]") {{
                  return null;
                }}
                if (selector === "[data-otoe-global-keydown]") {{
                  return null;
                }}
                if (selector.startsWith("[data-otoe-change=")) {{
                  return inputTarget;
                }}
                return null;
              }},
            }};

            global.document = document;
            global.window = {{CSS: {{escape(value) {{ return String(value).replace(/[\"\\\\]/g, "\\\\$&"); }}}}}};
            global.CSS = global.window.CSS;

            const pending = [];
            global.fetch = (url, options) => new Promise((resolve) => {{
              pending.push({{url, options, resolve}});
            }});

            const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

            (async () => {{
              eval(liveScript);

              inputTarget = {{
                dataset: {{otoeChange: "input:onChange"}},
                value: "first",
                selectionStart: 0,
                selectionEnd: 0,
                closest(selector) {{
                  if (selector === "[data-otoe-change]") {{
                    return this;
                  }}
                  return null;
                }},
                focus() {{
                  document.activeElement = this;
                }},
                setSelectionRange(start, end) {{
                  this.selectionStart = start;
                  this.selectionEnd = end;
                }},
                matches(selector) {{
                  return selector.includes("input");
                }},
              }};

              listeners.input({{target: inputTarget}});
              inputTarget.value = "second";
              listeners.input({{target: inputTarget}});

              pending[1].resolve({{
                json: async () => ({{ok: true, html: "second"}}),
              }});
              await flush();

              pending[0].resolve({{
                json: async () => ({{ok: true, html: "first"}}),
              }});
              await flush();

              if (root.innerHTML !== "second") {{
                throw new Error(`Expected latest response to win, got ${{root.innerHTML}}`);
              }}
            }})().catch((error) => {{
              console.error(error.stack || error.message || error);
              process.exit(1);
            }});
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["node", str(script)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stdout + result.stderr
