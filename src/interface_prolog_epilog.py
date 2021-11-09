"""Prolog and Epilog configs."""
from ops.framework import Object


class PrologEpilog(Object):
    """Prolog/Epilog interface."""

    def __init__(self, charm, relation_name):
        """Set the initial data."""
        super().__init__(charm, relation_name)
        self._charm = charm

        self.framework.observe(
            charm.on[relation_name].relation_created,
            self._on_relation_created
        )

    def _on_relation_created(self, event):
        event.relation.data[self.model.unit]['epilog'] = self._charm.epilog_path
        event.relation.data[self.model.unit]['prolog'] = self._charm.prolog_path
