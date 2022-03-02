"""LicenseManagerAgentOps."""
import logging
import subprocess
from pathlib import Path
from shutil import copy2, rmtree, chown

from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger()


class LicenseManagerAgentOps:
    """Track and perform license-manager-agent ops."""

    _PYTHON_BIN = Path("/usr/bin/python3.8")
    _PACKAGE_NAME = "license-manager-agent"
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _ETC_DEFAULT = Path("/etc/default/license-manager-agent")
    _SYSTEMD_BASE_PATH = Path("/usr/lib/systemd/system")
    _SYSTEMD_SERVICE_NAME = "license-manager-agent.service"
    _SYSTEMD_SERVICE_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_SERVICE_NAME
    _SYSTEMD_TIMER_NAME = "license-manager-agent.timer"
    _SYSTEMD_TIMER_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_TIMER_NAME
    _VENV_DIR = Path("/srv/license-manager-agent-venv")
    PROLOG_PATH = _VENV_DIR / "bin/slurmctld_prolog"
    EPILOG_PATH = _VENV_DIR / "bin/slurmctld_epilog"
    _PIP_CMD = _VENV_DIR.joinpath("bin", "pip3.8").as_posix()
    _SLURM_USER = "slurm"
    _SLURM_GROUP = "slurm"

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def _derived_pypi_url(self):
        url = self._charm.model.config["pypi-url"]
        url = url.split("://")[1]
        pypi_username = self._charm.model.config["pypi-username"]
        pypi_password = self._charm.model.config["pypi-password"]
        return (f"https://{pypi_username}:{pypi_password}@"
                f"{url}/simple/{self._PACKAGE_NAME}")

    def install(self):
        """Install license-manager-agent and setup ops."""

        # Create log dir
        if not self._LOG_DIR.exists():
            self._LOG_DIR.mkdir(parents=True)
        chown(self._LOG_DIR.as_posix(), self._SLURM_USER, self._SLURM_GROUP)

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
            "--use-deprecated=html5lib",
            "--upgrade",
            "pip",
        ]
        subprocess.call(upgrade_pip_cmd)

        pip_install_cmd = [
            self._PIP_CMD,
            "install",
            "--use-deprecated=html5lib",
            "-f",
            self._derived_pypi_url(),
            self._PACKAGE_NAME,
        ]
        logger.debug(f"## Running: {pip_install_cmd}")
        try:
            out = subprocess.check_output(pip_install_cmd, env={}).decode().strip()
            logger.debug("license-manager-agent installed")
            logger.debug(f"## pip install output: {out}")
        except Exception as e:
            logger.error(f"Error installing license-manager: {e}")
            raise Exception("License manager not installed.")

        # Copy the prolog/epilog wrappers
        copy2("./src/templates/slurmctld_prolog.sh", self.PROLOG_PATH)
        copy2("./src/templates/slurmctld_epilog.sh", self.EPILOG_PATH)

        self.setup_systemd_service()
        # Enable the systemd timer
        self.license_manager_agent_systemctl("enable")

    def setup_systemd_service(self):
        """Set up Systemd service and timer."""
        copy2("./src/templates/license-manager-agent.service",
              self._SYSTEMD_SERVICE_FILE.as_posix())

        charm_config = self._charm.model.config
        stat_interval = charm_config.get("stat-interval")
        ctxt = {"stat_interval": stat_interval}

        template_dir = Path("./src/templates/")
        environment = Environment(loader=FileSystemLoader(template_dir))
        template = environment.get_template(self._SYSTEMD_TIMER_NAME)

        rendered_template = template.render(ctxt)
        self._SYSTEMD_TIMER_FILE.write_text(rendered_template)

        subprocess.call(["systemctl", "daemon-reload"])

    def upgrade(self, version: str):
        """Upgrade license-manager-agent."""

        # Stop license-manager-agent
        self.license_manager_agent_systemctl("stop")

        pip_install_cmd = [
            self._PIP_CMD,
            "install",
            "--use-deprecated=html5lib",
            "--upgrade",
            "-f",
            self._derived_pypi_url(),
            f"{self._PACKAGE_NAME}=={version}",
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
        backend_base_url = charm_config.get("license-manager-backend-base-url")

        log_level = charm_config.get("log-level")
        sentry_dsn = charm_config.get("sentry-dsn")

        lmutil_path = charm_config.get("lmutil-path")
        rlmutil_path = charm_config.get("rlmutil-path")
        lsdyna_path = charm_config.get("lsdyna-path")
        lmxendutil_path = charm_config.get("lmxendutil-path")
        auth0_domain = charm_config.get("auth0-domain")
        auth0_audience = charm_config.get("auth0-audience")
        auth0_client_id = charm_config.get("auth0-client-id")
        auth0_client_secret = charm_config.get("auth0-client-secret")

        log_base_dir = str(self._LOG_DIR)

        ctxt = {
            "sentry_dsn": sentry_dsn,
            "log_level": log_level,
            "log_base_dir": log_base_dir,
            "license_manager_backend_base_url": backend_base_url,
            "lmutil_path": lmutil_path,
            "rlmutil_path": rlmutil_path,
            "lsdyna_path": lsdyna_path,
            "lmxendutil_path": lmxendutil_path,
            "auth0_domain": auth0_domain,
            "auth0_audience": auth0_audience,
            "auth0_client_id": auth0_client_id,
            "auth0_client_secret": auth0_client_secret,
        }

        template_dir = Path("./src/templates/")
        template_file = "license-manager.defaults.template"
        environment = Environment(loader=FileSystemLoader(template_dir))
        template = environment.get_template(template_file)

        rendered_template = template.render(ctxt)

        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()

        self._ETC_DEFAULT.write_text(rendered_template)

    def license_manager_agent_systemctl(self, operation: str):
        """Run license-manager-agent systemctl command."""

        try:
            for service in [self._SYSTEMD_TIMER_NAME, self._SYSTEMD_SERVICE_NAME]:
                cmd = ["systemctl", operation, service]
                subprocess.call(cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")

    def restart_license_manager_agent(self):
        """Stop and start the license-manager-agent.

        NOTE: We should probably use reload instead. Using stop/start
        temporarily..
        """
        self.license_manager_agent_systemctl("stop")
        self.license_manager_agent_systemctl("start")

    def remove_license_manager_agent(self):
        """Remove the things we have created."""
        self.license_manager_agent_systemctl("stop")
        self.license_manager_agent_systemctl("disable")
        if self._SYSTEMD_SERVICE_FILE.exists():
            self._SYSTEMD_SERVICE_FILE.unlink()
        if self._SYSTEMD_TIMER_FILE.exists():
            self._SYSTEMD_TIMER_FILE.unlink()
        subprocess.call(["systemctl", "daemon-reload"])
        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()
        rmtree(self._LOG_DIR.as_posix(), ignore_errors=True)
        rmtree(self._VENV_DIR.as_posix(), ignore_errors=True)
