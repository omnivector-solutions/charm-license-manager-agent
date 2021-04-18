#!/usr/bin/env python3
"""LicenseManagerAgentCharm."""
import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from interface_prolog_epilog import PrologEpilog
from license_manager_agent_ops import LicenseManagerAgentOps


logger = logging.getLogger()


class LicenseManagerAgentCharm(CharmBase):
    """Facilitate License Manager Agent lifecycle."""

    _stored = StoredState()

    def __init__(self, *args):
        """Initialize and observe."""
        super().__init__(*args)

        self._stored.set_default(jwt_key=str())
        self._stored.set_default(server_addrs=str())
        self._stored.set_default(installed=False)
        self._stored.set_default(license_server_features=str())

        self._prolog_epilog = PrologEpilog(self, 'prolog-epilog')
        self._license_manager_agent_ops = LicenseManagerAgentOps(self)

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.config_changed: self._on_config_changed,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install license-manager agent."""
        self._license_manager_agent_ops.install()
        self._stored.installed = True
        # Log and set status
        logger.debug("license-manager agent installed")
        self.unit.status = ActiveStatus("lm-agent installed")

    def _on_config_changed(self, event):
        """Configure license-manager agent with charm config."""

        # Get the jwt-key from the charm config and check if it has changed.
        jwt_key_from_config = self.model.config.get("jwt-key")
        if jwt_key_from_config != self._stored.jwt_key:
            self._stored.jwt_key = jwt_key_from_config
            self._license_manager_agent_ops.configure_etc_default()

        license_server_features = self.model.config.get("license-server-features")
        if self._stored.set_default(license_server_features != license_server_features:
            self._license_manager_agent_ops.configure_license_server_features()


if __name__ == "__main__":
    main(LicenseManagerAgentCharm)
