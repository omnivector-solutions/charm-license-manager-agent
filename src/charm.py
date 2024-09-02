#!/usr/bin/env python3
"""LicenseManagerAgentCharm."""
import logging
from pathlib import Path

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

from interface_prolog_epilog import PrologEpilog
from license_manager_agent_ops import LicenseManagerAgentOps

from charms.fluentbit.v0.fluentbit import FluentbitClient


logger = logging.getLogger()


class LicenseManagerAgentCharm(CharmBase):
    """Facilitate License Manager Agent lifecycle."""

    _stored = StoredState()

    def __init__(self, *args):
        """Initialize and observe."""
        super().__init__(*args)

        self._stored.set_default(
            installed=False,
            init_started=False,
        )

        self._prolog_epilog = PrologEpilog(self, "prolog-epilog")

        self._license_manager_agent_ops = LicenseManagerAgentOps(self)

        self._fluentbit = FluentbitClient(self, "fluentbit")

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.upgrade_charm: self._on_upgrade,
            self.on.start: self._on_start,
            self.on.config_changed: self._on_config_changed,
            self.on.remove: self._on_remove,
            self.on.upgrade_action: self._on_upgrade_action,
            self.on.show_version_action: self._on_show_version_action,
            self.on["fluentbit"].relation_created: self._on_fluentbit_relation_created,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install license-manager-agent."""
        self.unit.set_workload_version(Path("version").read_text().strip())

        try:
            self._license_manager_agent_ops.install()
        except Exception as e:
            logger.error(f"Error installing agent: {e}")
            self.unit.status = BlockedStatus("Installation error")
            event.defer()
            raise

        self.unit.set_workload_version(Path("version").read_text().strip())

        # Log and set status
        logger.debug("license-manager agent installed")
        self.unit.status = ActiveStatus("license-manager-agent installed")
        self._stored.installed = True

    def _on_upgrade(self, event):
        """Perform upgrade operations."""
        self.unit.set_workload_version(Path("version").read_text().strip())

    def _on_show_version_action(self, event):
        """Show the info and version of license-manager-agent."""
        info = self._license_manager_agent_ops.get_version_info()
        event.set_results({"license-manager-agent": info})

    def _on_start(self, event):
        """Start the license-manager-agent service."""
        if self._stored.installed:
            self._license_manager_agent_ops.start_agent()
            self.unit.status = ActiveStatus("license-manager-agent started")
            self._stored.init_started = True

    def _on_config_changed(self, event):
        """Configure license-manager-agent with charm config."""
        self._license_manager_agent_ops.configure_etc_default()

        if self._stored.init_started:
            self._license_manager_agent_ops.restart_agent()

    def _on_remove(self, event):
        """Remove directories and files created by license-manager-agent charm."""
        self._license_manager_agent_ops.remove_agent()

    def _on_upgrade_action(self, event):
        version = event.params["version"]
        try:
            self._license_manager_agent_ops.upgrade(version)
            event.set_results({"upgrade": "success"})
            self.unit.status = ActiveStatus(f"Updated to version {version}")
            self._license_manager_agent_ops.restart_agent()
        except Exception:
            self.unit.status = BlockedStatus(f"Error updating to version {version}")
            event.fail()

    def _on_fluentbit_relation_created(self, event):
        """Set up Fluentbit log forwarding."""
        cfg = list()
        cfg.extend(self._license_manager_agent_ops.fluentbit_config_lm_log)
        self._fluentbit.configure(cfg)

    @property
    def prolog_path(self) -> str:
        """Return the path to the prolog script."""
        return self._license_manager_agent_ops._PROLOG_PATH.as_posix()

    @property
    def epilog_path(self) -> str:
        """Return the path to the epilog script."""
        return self._license_manager_agent_ops._EPILOG_PATH.as_posix()


if __name__ == "__main__":
    main(LicenseManagerAgentCharm)
