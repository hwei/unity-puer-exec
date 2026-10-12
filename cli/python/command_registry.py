"""Single declaration of the CLI's invocable command set.

Both the argparse surface and the help/guidance tables derive membership from
this registry so a command cannot be invocable while absent from help, or
documented while absent from the parser.

`COMMAND_GROUPS` / `COMMANDS` are the canonical, documented command set. A
deprecated alias such as `ensure-stopped` is invocable and answers the same help
tiers as the command it aliases, but it is not part of the canonical tree: it is
derived from `COMMAND_ALIASES` so parser, help, and guidance entries cannot
drift from the alias table.
"""

# (group title, ordered command names). Order is the top-level help order.
COMMAND_GROUPS = (
    (
        "Primary Execution",
        (
            "exec",
            "play",
            "pause",
            "stop",
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
            "ensure-closed",
            "get-compile-errors",
            "get-compile-warnings",
        ),
    ),
)

COMMANDS = tuple(command for _, commands in COMMAND_GROUPS for command in commands)

# Deprecated aliases. Ordered so help/guidance tables build deterministically.
# An alias name must never appear in COMMAND_GROUPS: it is derived surface, not
# a canonical command.
COMMAND_ALIASES = (
    ("ensure-stopped", "ensure-closed"),
)

ALIASES = dict(COMMAND_ALIASES)

# Every name the parser accepts. Canonical commands first, then derived aliases.
INVOCABLE_COMMANDS = COMMANDS + tuple(alias for alias, _ in COMMAND_ALIASES)


def canonical_command(name):
    """Return the canonical command for ``name``, resolving aliases."""
    return ALIASES.get(name, name)


def deprecation_for(name):
    """Return the alias-deprecation object for ``name``, or ``None``."""
    canonical = ALIASES.get(name)
    if canonical is None:
        return None
    return {"alias": name, "use": canonical}
