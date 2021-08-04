"""
LicenseManagerAgentOps.
"""
import logging
import subprocess

from pathlib import Path
from shutil import copy2, rmtree


logger = logging.getLogger()


class LicenseManagerAgentOps:
    """Track and perform license-manager-agent ops."""

    _PYTHON_BIN = Path("/usr/bin/python3.8")
    _PACKAGE_NAME = "license-manager[agent]"
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _ETC_DEFAULT = Path("/etc/default/license-manager-agent")
    _SYSTEMD_BASE_PATH = Path("/usr/lib/systemd/system")
    _SYSTEMD_SERVICE_NAME = "license-manager-agent.service"
    _SYSTEMD_SERVICE_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_SERVICE_NAME
    _VENV_DIR = Path("/srv/license-manager-agent-venv")
    _PIP_CMD = _VENV_DIR.joinpath("bin", "pip3.8").as_posix()

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def _derived_pypi_url(self):
        url = self._charm.model.config["pypi-url"]
        url = url.split("://")[1]
        pypi_username = self._charm.model.config["pypi-username"]
        pypi_password = self._charm.model.config["pypi-password"]
        return (f"https://{pypi_username}:{pypi_password}@"
                f"{url}/simple/{self._PACKAGE_NAME[:15]}")

    def install(self):
        """Install license-manager-agent and setup ops."""

        # Create log dir
        if not self._LOG_DIR.exists():
            self._LOG_DIR.mkdir(parents=True)

        # Create the virtualenv
        create_venv_cmd = [
            self._PYTHON_BIN.as_posix(),
            "-m",
            "venv",
            self._VENV_DIR.as_posix(),
        ]
        subprocess.call(create_venv_cmd)
        logger.debug("license-manager-agent virtualenv created")

        # Ensure we have the latest pip
        upgrade_pip_cmd = [
            self._PIP_CMD,
            "install",
            "--upgrade",
            "pip",
        ]
        subprocess.call(upgrade_pip_cmd)

        pip_install_cmd = [
            self._PIP_CMD,
            "install",
            "-f",
            self._derived_pypi_url(),
            self._PACKAGE_NAME,
        ]
        out = subprocess.check_output(pip_install_cmd).decode().strip()
        if "Successfully installed" not in out:
            logger.error("Trouble installing license-manager, please debug")
            raise Exception("License manager not installed.")
        else:
            logger.debug("license-manager-agent installed")

        # Copy the prolog/epilog wrappers
        copy2(
            "./src/templates/slurmctld_prolog.sh",
            "/srv/license-manager-agent-venv/bin/slurmctld_prolog"
        )
        copy2(
            "./src/templates/slurmctld_epilog.sh",
            "/srv/license-manager-agent-venv/bin/slurmctld_epilog"
        )

        # Setup systemd service file
        copy2(
            "./src/templates/license-manager-agent.service",
            self._SYSTEMD_SERVICE_FILE.as_posix()
        )

        # Enable the systemd service
        subprocess.call([
            "systemctl",
            "enable",
            self._SYSTEMD_SERVICE_NAME,
        ])

    def upgrade(self, version: str):
        """Upgrade license-manager-agent."""
        
        # Stop license-manager-agent
        self.license_manager_agent_systemctl("stop")

        pip_install_cmd = [
            self._PIP_CMD,
            "install",
            "--upgrade",
            "-f",
            self._derived_pypi_url(),
            f"{self._PACKAGE_NAME}={version}",
        ]

        out = subprocess.check_output(pip_install_cmd).decode().strip()
        if "Successfully installed" not in out:
            logger.error("Trouble upgrading license-manager, please debug")
            raise Exception("License manager not installed.")
        else:
            logger.debug("license-manager-agent installed")
            # Start license-manager-agent
            self.license_manager_agent_systemctl("start")

    def configure_etc_default(self):
        """Get the needed config, render and write out the file."""
        charm_config = self._charm.model.config
        jwt_key = charm_config.get("jwt-key")
        backend_base_url = charm_config.get("license-manager-backend-base-url")

        log_level = charm_config.get("log-level")
        stat_interval = charm_config.get("stat-interval")

        log_base_dir = str(self._LOG_DIR)

        ctxt = {
            "log_level": log_level,
            "jwt_key": jwt_key,
            "stat_interval": stat_interval,
            "log_base_dir": log_base_dir,
            "license_manager_backend_base_url": backend_base_url,
        }

        etc_default_template = Path(
            "./src/templates/license-manager.defaults.template").read_text()

        rendered_template = etc_default_template.format(**ctxt)

        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()

        self._ETC_DEFAULT.write_text(rendered_template)
    
    def license_manager_agent_systemctl(self, operation: str):
        """
        Run license-manager-agent systemctl command.
        """
        cmd = [
            "systemctl",
            operation,
            self._SYSTEMD_SERVICE_NAME,
        ]
        try:
            subprocess.call(cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")

    def restart_license_manager_agent(self):
        """
        Stop and start the license-manager-agent.

        NOTE: We should probably use reload instead. Using stop/start
        temporarily..
        """
        # Stop license-manager-agent
        self.license_manager_agent_systemctl("stop")
        # Start license-manager-agent
        self.license_manager_agent_systemctl("start")

    def remove_license_manager_agent(self):
        """
        Remove the things we have created.
        """
        self.license_manager_agent_systemctl("stop")
        self.license_manager_agent_systemctl("disable")
        if self._SYSTEMD_SERVICE_FILE.exists():
            self._SYSTEMD_SERVICE_FILE.unlink()
        subprocess.call([
            "systemctl",
            "daemon-reload"
        ])
        self._ETC_DEFAULT.unlink()
        rmtree(self._LOG_DIR.as_posix())
        rmtree(self._VENV_DIR.as_posix())
