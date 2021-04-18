"""
LicenseManagerAgentOps.
"""
import logging
import subprocess
from pathlib import Path
from shutil import rmtree


logger = logging.getLogger()


class LicenseManagerAgentOps:
    """Track and perform license-manager-agent ops."""

    _LICENSE_MANAGER_AGENT_PACKAGE_NAME = "license-manager[dev]"
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _CONFIG_DIR = Path("/etc/license-manager-agent")
    _ETC_DEFAULT = Path("/etc/default/license-manager")
    _LICENSE_SERVER_FEATURES_CONFIG_PATH = _CONFIG_DIR / "license-server-features.yaml"
    _LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_NAME = "license-manager-agent.service"
    _LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_FILE = Path(
        f"/etc/systemd/system/{_LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_NAME}"
    )
    _LICENSE_MANAGER_AGENT_VENV_DIR = Path("/srv/license-manager-agent-venv")

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def install(self):
        """Install license-manager-agent and setup ops."""
        pypi_url = self._charm.model.config["pypi-url"]
        pypi_username = self._charm.model.config["pypi-username"]
        pypi_password = self._charm.model.config["pypi-password"]

        # Create log dir
        if not self._LOG_DIR.exists():
            self._LOG_DIR.mkdir(parents=True)

        # Create config dir
        if not self._CONFIG_DIR.exists():
            self._CONFIG_DIR.mkdir(parents=True)

        # Create the virtualenv
        create_venv_cmd = [
            "python3.8",
            "-m",
            "venv",
            str(self._LICENSE_MANAGER_AGENT_VENV_DIR),
        ]
        subprocess.call(create_venv_cmd)
        logger.debug("license-manager-agent virtualenv created")

        # Install license-manager-agent
        url = pypi_url.split("://")[1]
        pip_install_cmd = [
            "/srv/license-manager-agent-venv/bin/pip3.8",
            "install",
            "-f",
            f"https://{pypi_username}:{pypi_password}@{url}",
            self._LICENSE_MANAGER_AGENT_PACKAGE_NAME,
        ]
        subprocess.call(pip_install_cmd)
        logger.debug("license-manager-agent installed")

        # Setup systemd
        systemd_service_template = Path(
            "./src/templates/license-manager-agent.service").read_text()

        self._LICENSE_SERVER_AGENT_SYSTEMD_SERVICE_FILE.write_text(
            systemd_service_template
        )
        subprocess.call([
            "systemctl",
            "enable",
            self._LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_NAME,
        ])

    def configure_etc_default(self):
        """Get the needed config, render and write out the file."""
        charm_config = self._charm.model.config
        jwt_key = charm_config.get("jwt-key")
        backend_base_url = charm_config.get("license-manager-backend-base-url")
        service_addrs = charm_config.get("service-addrs")
        license_server_features_path = str(
            self._LICENSE_SERVER_FEATURES_CONFIG_PATH
        )

        ctxt = {
            "jwt_key": jwt_key,
            "service_addrs": service_addrs,
            "license_manager_backend_base_url": backend_base_url,
            "license_server_features_path": license_server_features_path,
        }

        etc_default_template = Path(
            "./src/templates/license-manager.defaults.template").read_text()

        rendered_template = etc_default_template.format(**ctxt)

        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()

        self._ETC_DEFAULT.write_text(rendered_template)

    def configure_license_server_features(self):
        """Write out the license-server-features.yaml"""
        if self._LICENSE_SERVER_FEATURES_CONFIG_PATH.exists():
            self._LICENSE_SERVER_FEATURES_CONFIG_PATH.unlink()
        self._LICENSE_SERVER_FEATURES_CONFIG_PATH.write_text(
            self._charm.model.config.get("license-server-features")
        )

    def stop_license_manager_agent(self):
        """
        Stop the license-manager-agent systemd process.
        """
        stop_cmd = [
            "systemctl",
            "stop",
            self._LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_NAME,
        ]
        try:
            subprocess.call(stop_cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(stop_cmd)} - {e}")

    def start_license_manager_agent(self):
        """
        Start the license-manager-agent.
        """
        start_cmd = [
            "systemctl",
            "start",
            self._LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_NAME,
        ]
        try:
            subprocess.call(start_cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(start_cmd)} - {e}")

    def restart_license_manager_agent(self):
        """
        Stop and start the license-manager-agent.

        NOTE: We should probably use reload instead. Using stop/start
        temporarily..
        """
        # Stop license-manager-agent
        self.stop_license_manager_agent()
        # Start license-manager-agent
        self.start_license_manager_agent()

    def remove_license_manager_agent(self):
        """
        Remove the things we have created.
        """
        self._ETC_DEFAULT.unlink()
        self._LICENSE_MANAGER_AGENT_SYSTEMD_SERVICE_FILE.unlink()
        rmtree(str(self._CONFIG_DIR))
        rmtree(str(self._LOG_DIR))
        rmtree(str(self._LICENSE_MANAGER_AGENT_VENV_DIR))
