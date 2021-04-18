#!/usr/bin/python3
"""Prolog and Epilog configs."""
from ops.framework import Object


class PrologEpilog(Object):
    """Prolog/Epilog interface."""

    def __init__(self, charm, relation_name):
        """Set the initial data."""
        super().__init__(charm, relation_name)

        self.framework.observe(
            charm.on[relation_name].relation_created,
            self._on_relation_created
        )

    def _on_relation_created(self, event):
        prolog = "/srv/license-manager-agent-venv/bin/slurmctld-prolog"
        epilog = "/srv/license-manager-agent-venv/bin/slurmctld-epilog"
        event.relation.data[self.model.unit]['epilog'] = epilog
        event.relation.data[self.model.unit]['prolog'] = prolog
