"""Single declaration of the CLI's invocable command set.

Both the argparse surface and the help/guidance tables derive membership from
this registry so a command cannot be invocable while absent from help, or
documented while absent from the parser.
"""

# (group title, ordered command names). Order is the top-level help order.
COMMAND_GROUPS = (
    (
        "Primary Execution",
        (
            "exec",
        ),
    ),
    (
        "Supporting Observation",
        (
            "wait-for-exec",
            "wait-for-result-marker",
            "wait-for-log-pattern",
            "wait-for-compile",
        ),
    ),
    (
        "Secondary / Troubleshooting",
        (
            "get-log-source",
            "get-log-briefs",
            "get-blocker-state",
            "resolve-blocker",
            "ensure-stopped",
            "get-compile-errors",
            "get-compile-warnings",
        ),
    ),
)

COMMANDS = tuple(command for _, commands in COMMAND_GROUPS for command in commands)
