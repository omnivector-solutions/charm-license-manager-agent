"""
LicenseManagerAgentOps.
"""
import subprocess
from pathlib import Path


class LicenseManagerAgentOps:
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _CONFIG_DIR = Path("/etc/license-manager-agent")
    _ETC_DEFAULT = Path("/etc/default/license-manager")
    _LICENSE_SERVER_FEATURES_CONFIG_PATH = str(
        _CONFIG_DIR / "license-server-features.yaml"
    )
    _LICENSE_SERVER_AGENT_SYSTEMD_SERVICE = Path(
        "/etc/systemd/system/license-manager-agent.service"
    )

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def install(self, pypi_url, pypi_username, pypi_password):
        """Install license-manager-agent and setup ops."""

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
            "/srv/license-manager-agent-venv"
        ]
        subprocess.call(create_venv_cmd)

        # Install license-manager-agent
        url = pypi_url.split("://")[1]
        pip_install_cmd = [
            "/srv/license-manager-agent-venv/bin/pip3.8",
            "install",
            "-f"
            f"https://{pypi_username}:{pypi_password}@{url}"
            "license-manager"
        ]
        subprocess.call(pip_install_cmd)

        # Setup systemd
        systemd_service_template = Path(
            "./src/templates/license-manager-agent.service").read_text()

        self._LICENSE_SERVER_AGENT_SYSTEMD_SERVICE.write_text(
            systemd_service_template
        )
        subprocess.call([
            "systemctl",
            "enable",
            "license-manager-agent.service",
        ])

    def configure_etc_default(self):
        """Get the needed config, render and write out the file."""
        charm_config = self._charm.model.config
        jwt_key = charm_config.get("jwt-key")
        backend_base_url = charm_config.get("license-manager-backend-base-url")
        service_addrs = charm_config.get("service-addrs")
        license_server_features_path = str(self._LICENSE_SERVER_FEATURES_CONFIG_PATH)

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
