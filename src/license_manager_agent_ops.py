"""LicenseManagerAgentOps."""
import logging
import subprocess
from pathlib import Path
from shutil import chown, copy2, rmtree

logger = logging.getLogger()


class LicenseManagerAgentOps:
    """Track and perform license-manager-agent ops."""

    _PACKAGE_NAME = "license-manager-agent"
    _SYSTEMD_SERVICE_NAME = "license-manager-agent.service"
    _SYSTEMD_BASE_PATH = Path("/usr/lib/systemd/system")
    _SYSTEMD_SERVICE_ALIAS = f"{_PACKAGE_NAME}.service"
    _SYSTEMD_SERVICE_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_SERVICE_ALIAS
    _VENV_DIR = Path("/srv/license-manager-agent-venv")
    _ENV_DEFAULTS = Path("/etc/default/license-manager-agent")
    _PIP_CMD = _VENV_DIR.joinpath("bin", "pip").as_posix()
    _PYTHON_CMD = Path("/opt/python/python3.12/bin/python3.12")
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _CACHE_DIR = Path("/var/cache/license-manager")
    _PROLOG_PATH = _VENV_DIR / "bin/slurmctld_prolog"
    _EPILOG_PATH = _VENV_DIR / "bin/slurmctld_epilog"
    _SLURM_USER = "slurm"
    _SLURM_GROUP = "slurm"
    _LICENSE_MANAGER_USER = "license-manager"
    _LICENSE_MANAGER_ACCOUNT = "license-manager"

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def install(self):
        """Install license-manager-agent and set up ops."""
        # Create the virtualenv and ensure pip is up to date.
        self._create_venv_and_ensure_latest_pip()

        # Install license-manager-agent
        self._install_license_manager_agent()

        # Setup cache dir
        self._setup_cache_dir()

        # Setup log dir
        self._setup_log_dir()

        # Setup license-manager user
        self._setup_license_manager_user()

        # Setup prolog and epilog scripts
        self._setup_prolog_epilog()

        # Setup systemd service
        self._setup_systemd()

        # Enable the systemd service
        self.systemctl("enable")

    def upgrade(self, version: str):
        """Upgrade license-manager-agent."""
        self._setup_cache_dir()
        self.systemctl("stop")
        self._upgrade_license_manager_agent(version)

    def get_version_info(self):
        """Show version and info about license-manager-agent."""
        cmd = [self._PIP_CMD, "show", self._PACKAGE_NAME]

        out = subprocess.check_output(cmd, env={}).decode().strip()

        return out

    def _setup_cache_dir(self):
        """Set up cache dir."""
        # Delete cache dir if it already exists
        if self._CACHE_DIR.exists():
            logger.debug(
                f"The cache directory already exists. Clearing it: {self._CACHE_DIR.as_posix()}"
            )
            rmtree(self._CACHE_DIR, ignore_errors=True)
        else:
            logger.debug(
                f"Searched for the cache directory {self._CACHE_DIR.as_posix()}, \
                but it does not exist; skipping for its creation"
            )

        # Create a clean cache dir
        logger.debug(f"Creating a clean cache dir {self._CACHE_DIR.as_posix()}")
        self._CACHE_DIR.mkdir(parents=True)
        chown(self._CACHE_DIR.as_posix(), self._SLURM_USER, self._SLURM_GROUP)
        self._CACHE_DIR.chmod(0o777)

    def _setup_log_dir(self):
        """Set up log dir."""
        # Delete log dir if it already exists
        if self._LOG_DIR.exists():
            logger.debug(
                f"The log directory already exists. Clearing it: {self._LOG_DIR.as_posix()}"
            )
            rmtree(self._LOG_DIR, ignore_errors=True)
        else:
            logger.debug(
                f"Tried to clean log dir {self._LOG_DIR.as_posix()}, but it does not exist"
            )

        # Create a clean log dir
        logger.debug(f"Creating a clean log dir {self._LOG_DIR.as_posix()}")
        self._LOG_DIR.mkdir(parents=True)
        chown(self._LOG_DIR.as_posix(), self._SLURM_USER, self._SLURM_GROUP)
        self._LOG_DIR.chmod(0o777)

    def _setup_license_manager_user(self):
        """Set up license-manager user, account and group."""
        # Create the license-manager-agent user
        useradd_cmd = [
            "adduser",
            "--system",
            "--no-create-home",
            self._LICENSE_MANAGER_USER,
        ]
        subprocess.call(useradd_cmd)
        logger.debug("license-manager-agent user created")

        # Add user to slurm group
        usermod_cmd = [
            "usermod",
            "-a",
            "-G",
            self._SLURM_GROUP,
            self._LICENSE_MANAGER_USER,
        ]
        subprocess.call(usermod_cmd)
        logger.debug("license-manager-agent user added to slurm group")

        # Create the Slurm account for License Manager
        create_account_cmd = [
            "sacctmgr",
            "add",
            "account",
            self._LICENSE_MANAGER_ACCOUNT,
            "Description=License Manager reservations account",
            "-i",
        ]
        subprocess.call(create_account_cmd)
        logger.debug("license-manager-agent account created")

        # Add license-manager-agent user to License Manager account
        # Operator level ensures they can create reservations
        add_to_account_cmd = [
            "sacctmgr",
            "add",
            "user",
            self._LICENSE_MANAGER_USER,
            f"Account={self._LICENSE_MANAGER_ACCOUNT}",
            "AdminLevel=Operator",
            "-i",
        ]
        subprocess.call(add_to_account_cmd)
        logger.debug(
            "license-manager-agent user added to account with operator admin level"
        )

    def _create_venv_and_ensure_latest_pip(self):
        """Create the virtualenv and ensure pip is up to date."""
        # Create the virtualenv
        create_venv_cmd = [
            self._PYTHON_CMD,
            "-m",
            "venv",
            self._VENV_DIR.as_posix(),
        ]
        logger.debug(f"## Creating virtualenv: {create_venv_cmd}")
        subprocess.call(create_venv_cmd, env={})
        logger.debug("## license-manager-agent virtualenv created")

        # Ensure we have the latest pip
        upgrade_pip_cmd = [
            self._PIP_CMD,
            "install",
            "--upgrade",
            "pip",
        ]
        logger.debug(f"## Upgrading pip: {upgrade_pip_cmd}")
        subprocess.call(upgrade_pip_cmd, env={})
        logger.debug("## pip upgraded")

    def _install_license_manager_agent(self):
        """Install license-manager-agent package."""
        cmd = [
            self._PIP_CMD,
            "install",
            self._PACKAGE_NAME,
        ]
        logger.debug(f"## Installing license-manager-agent: {cmd}")
        try:
            subprocess.call(cmd, env={})
            logger.debug("license-manager-agent installed")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def _upgrade_license_manager_agent(self, version: str):
        """Upgrade license-manager-agent package."""
        cmd = [
            self._PIP_CMD,
            "install",
            "--upgrade",
            f"self._PACKAGE_NAME=={version}",
        ]
        logger.debug(f"## Upgrading license-manager-agent: {cmd}")
        try:
            subprocess.call(cmd, env={})
            logger.debug("license-manager-agent upgraded")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running {' '.join(cmd)} - {e}")
            raise e

    def _setup_prolog_epilog(self):
        """Setup prolog and epilog scripts."""

        copy2("./src/templates/slurmctld_prolog.sh", self._PROLOG_PATH)
        copy2("./src/templates/slurmctld_epilog.sh", self._EPILOG_PATH)

    def _setup_systemd(self):
        """Provision the license0manager-agent systemd service."""
        copy2(
            "./src/templates/license-manager-agent.service",
            self._SYSTEMD_SERVICE_FILE.as_posix(),
        )

        subprocess.call(["systemctl", "daemon-reload"])
        subprocess.call(["systemctl", "enable", "--now", self._SYSTEMD_SERVICE_ALIAS])

    def systemctl(self, operation: str):
        """
        Run systemctl operation for the service.
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

    def configure_etc_default(self):
        """Get the needed config, render and write out the file."""
        prefix = "LM_AGENT_"
        charm_config = self._charm.model.config

        ctxt = {
            key.replace("-", "_").upper(): value for key, value in charm_config.items()
        }

        with open(self._ENV_DEFAULTS, "w") as env_file:
            for key, value in ctxt.items():
                print(f"{prefix}{key}={value}", file=env_file)

        # Clear cache dir after upgrade to avoid stale data
        self._setup_cache_dir()

    def start_agent(self):
        """Start the license-manager-agent service."""
        self.systemctl("start")

    def stop_agent(self):
        """Stop the license-manager-agent service."""
        self.systemctl("stop")

    def restart_agent(self):
        """Restart the license-manager-agent service."""
        self.systemctl("restart")

    def remove_agent(self):
        """Remove the things we have created."""
        self.systemctl("stop")
        self.systemctl("disable")
        if self._SYSTEMD_SERVICE_FILE.exists():
            self._SYSTEMD_SERVICE_FILE.unlink()
        subprocess.call(["systemctl", "daemon-reload"])
        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()
        rmtree(self._LOG_DIR.as_posix(), ignore_errors=True)
        rmtree(self._CACHE_DIR.as_posix(), ignore_errors=True)
        rmtree(self._VENV_DIR.as_posix(), ignore_errors=True)

        # Remove the agent user from the License Manager Slurm account
        remove_user_cmd = [
            "sacctmgr",
            "remove",
            "user",
            self._LICENSE_MANAGER_USER,
            "-i",
        ]
        subprocess.call(remove_user_cmd)

        # Remove the License Manager Slurm account
        remove_account_cmd = [
            "sacctmgr",
            "remove",
            "account",
            self._LICENSE_MANAGER_ACCOUNT,
            "-i",
        ]
        subprocess.call(remove_account_cmd)

        # Remove the agent user
        subprocess.call(["userdel", self._LICENSE_MANAGER_USER])

    @property
    def fluentbit_config_lm_log(self) -> list:
        """Return Fluentbit configuration parameters to forward LM agent logs."""
        cfg = [
            {
                "input": [
                    ("name", "tail"),
                    ("path", "/var/log/license-manager-agent/*.log"),
                    ("tag", "lm.*"),
                    ("multiline.parser", "multiline-lm"),
                ]
            },
            {
                "multiline_parser": [
                    ("name", "multiline-lm"),
                    ("type", "regex"),
                    ("flush_timeout", "1000"),
                    (
                        "rule",
                        '"start_state"',
                        '"/^\[(\d+(\-)?){3} (\d+(\:)?){3},\d+\;\w+\] .+/"',
                        '"cont"',
                    ),  # noqa
                    ("rule", '"cont"', '"/^([^\[].*)/"', '"cont"'),
                ]
            },
        ]  # noqa
        return cfg
