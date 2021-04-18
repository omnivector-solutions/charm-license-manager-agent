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
        self._stored.set_default(service_addrs=str())
        self._stored.set_default(init_started=False)
        self._stored.set_default(installed=False)
        self._stored.set_default(license_server_features=str())
        self._stored.set_default(backend_base_url=str())

        self._prolog_epilog = PrologEpilog(self, 'prolog-epilog')
        self._license_manager_agent_ops = LicenseManagerAgentOps(self)

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.start: self._on_start,
            self.on.config_changed: self._on_config_changed,
            self.on.remove: self._on_remove,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install license-manager-agent."""
        self._license_manager_agent_ops.install()
        self._stored.installed = True
        # Log and set status
        logger.debug("license-manager agent installed")
        self.unit.status = ActiveStatus("license-manager-agent installed")

    def _on_start(self, event):
        """Start the license-manager-agent service."""
        if self._stored.installed:
            self._license_manager_agent_ops.start_license_manager_agent()
            self._stored.init_started = True
            self.unit.status = ActiveStatus("license-manager-agent started")

    def _on_config_changed(self, event):
        """Configure license-manager-agent with charm config."""

        # Get the backend-base-url from the charm config and check if it has changed.
        backend_base_url_from_config = self.model.config.get("backend-base-url")
        if backend_base_url_from_config != self._stored.backend_base_url:
            self._stored.backend_base_url = backend_base_url_from_config
            self._license_manager_agent_ops.configure_etc_default()

        # Get the service-addrs from the charm config and check if it has changed.
        service_addrs_from_config = self.model.config.get("service-addrs")
        if service_addrs_from_config != self._stored.service_addrs:
            self._stored.service_addrs = service_addrs_from_config
            self._license_manager_agent_ops.configure_etc_default()

        # Get the jwt-key from the charm config and check if it has changed.
        jwt_key_from_config = self.model.config.get("jwt-key")
        if jwt_key_from_config != self._stored.jwt_key:
            self._stored.jwt_key = jwt_key_from_config
            self._license_manager_agent_ops.configure_etc_default()

        license_server_features = self.model.config.get("license-server-features")
        if license_server_features != self._stored.license_server_features:
            self._license_manager_agent_ops.configure_license_server_features()

        # Make sure the start hook has ran before we are restarting the service
        if self._stored.init_started:
            self._license_manager_agent_ops.restart_license_manager_agent()

    def _on_remove(self, event):
        """Remove directories and files created by license-manager-agent charm."""
        self._license_manager_agent_ops.stop_license_manager_agent()
        self._license_manager_agent_ops.remove_license_manager_agent()


if __name__ == "__main__":
    main(LicenseManagerAgentCharm)
