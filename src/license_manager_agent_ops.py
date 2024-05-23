"""LicenseManagerAgentOps."""
import logging
import subprocess
from pathlib import Path
from shutil import chown, copy2, rmtree

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger()


class LicenseManagerAgentOps:
    """Track and perform license-manager-agent ops."""

    _PYTHON_BIN = Path("/opt/python/python3.12/bin/python3.12")
    _PACKAGE_NAME = "license-manager-agent"
    _LOG_DIR = Path("/var/log/license-manager-agent")
    _CACHE_DIR = Path("/var/cache/license-manager")
    _ETC_DEFAULT = Path("/etc/default/license-manager-agent")
    _SYSTEMD_BASE_PATH = Path("/usr/lib/systemd/system")
    _SYSTEMD_SERVICE_NAME = "license-manager-agent.service"
    _SYSTEMD_SERVICE_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_SERVICE_NAME
    _SYSTEMD_TIMER_NAME = "license-manager-agent.timer"
    _SYSTEMD_TIMER_FILE = _SYSTEMD_BASE_PATH / _SYSTEMD_TIMER_NAME
    _VENV_DIR = Path("/srv/license-manager-agent-venv")
    _VENV_PYTHON = _VENV_DIR.joinpath("bin", "python").as_posix()
    PROLOG_PATH = _VENV_DIR / "bin/slurmctld_prolog"
    EPILOG_PATH = _VENV_DIR / "bin/slurmctld_epilog"
    _SLURM_USER = "slurm"
    _SLURM_GROUP = "slurm"
    _LICENSE_MANAGER_USER = "license-manager"
    _LICENSE_MANAGER_ACCOUNT = "license-manager"

    def __init__(self, charm):
        """Initialize license-manager-agent-ops."""
        self._charm = charm

    def setup_cache_dir(self):
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

    def setup_log_dir(self):
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

    def setup_license_manager_user(self):
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
        logger.debug("license-manager-agent user added to account with operator admin level")

    def install(self):
        """Install license-manager-agent and set up ops."""
        # Create the virtualenv
        create_venv_cmd = [
            self._PYTHON_BIN.as_posix(),
            "-m",
            "venv",
            self._VENV_DIR.as_posix(),
        ]
        subprocess.call(create_venv_cmd)
        logger.debug("license-manager-agent virtualenv created")

        # Ensure pip
        ensure_pip_cmd = [
            self._VENV_PYTHON,
            "-m",
            "ensurepip",
        ]
        subprocess.check_output(ensure_pip_cmd, env={})
        logger.debug("pip ensured")

        # Ensure we have the latest pip
        upgrade_pip_cmd = [
            self._VENV_PYTHON,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        ]
        subprocess.call(upgrade_pip_cmd)

        pip_install_cmd = [
            self._VENV_PYTHON,
            "-m",
            "pip",
            "install",
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

        # Setup cache dir
        self.setup_cache_dir()

        # Setup log dir
        self.setup_log_dir()

        # Setup license-manager user
        self.setup_license_manager_user()

        # Setup systemd service and timer
        self.setup_systemd_service()

        # Enable the systemd timer
        self.license_manager_agent_systemctl("enable")

    def setup_systemd_service(self):
        """Set up Systemd service and timer."""
        charm_config = self._charm.model.config
        stat_interval = charm_config.get("stat-interval")
        timeout_interval = charm_config.get("timeout-interval")
        ctxt = {
            "stat_interval": stat_interval,
            "timeout_interval": timeout_interval,
        }
        template_dir = Path("./src/templates/")
        environment = Environment(loader=FileSystemLoader(template_dir))

        timer_template_file = "license-manager-agent.timer.template"
        timer_template = environment.get_template(timer_template_file)
        timer_rendered_template = timer_template.render(ctxt)
        self._SYSTEMD_TIMER_FILE.write_text(timer_rendered_template)

        service_template_file = "license-manager-agent.service.template"
        service_template = environment.get_template(service_template_file)
        service_rendered_template = service_template.render(ctxt)
        self._SYSTEMD_SERVICE_FILE.write_text(service_rendered_template)

        subprocess.call(["systemctl", "daemon-reload"])

    def upgrade(self, version: str):
        """Upgrade license-manager-agent."""

        # Stop license-manager-agent
        self.license_manager_agent_systemctl("stop")

        pip_install_cmd = [
            self._VENV_PYTHON,
            "-m",
            "pip",
            "install",
            "--upgrade",
            f"{self._PACKAGE_NAME}=={version}",
        ]

        out = subprocess.check_output(pip_install_cmd, env={}).decode().strip()

        if "Successfully installed" not in out:
            logger.error("Trouble upgrading license-manager, please debug")
        else:
            logger.debug("license-manager-agent installed")
            # Start license-manager-agent
            self.license_manager_agent_systemctl("start")

        # Clear cache dir after upgrade to avoid stale data
        self.setup_cache_dir()

    def get_version_info(self):
        """Show version and info about license-manager-agent."""
        cmd = [
            self._VENV_PYTHON,
            "-m",
            "pip",
            "show",
            self._PACKAGE_NAME
        ]

        out = subprocess.check_output(cmd, env={}).decode().strip()

        return out

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
        olixtool_path = charm_config.get("olixtool-path")
        oidc_domain = charm_config.get("oidc-domain")
        oidc_audience = charm_config.get("oidc-audience")
        oidc_client_id = charm_config.get("oidc-client-id")
        oidc_client_secret = charm_config.get("oidc-client-secret")
        use_reconcile_in_prolog_epilog = charm_config.get(
            "use-reconcile-in-prolog-epilog"
        )
        deploy_env = charm_config.get("deploy-env")
        stat_interval = charm_config.get("stat-interval")

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
            "olixtool_path": olixtool_path,
            "oidc_domain": oidc_domain,
            "oidc_audience": oidc_audience,
            "oidc_client_id": oidc_client_id,
            "oidc_client_secret": oidc_client_secret,
            "use_reconcile_in_prolog_epilog": use_reconcile_in_prolog_epilog,
            "deploy_env": deploy_env,
            "stat_interval": stat_interval,
        }

        template_dir = Path("./src/templates/")
        template_file = "license-manager.defaults.template"
        environment = Environment(loader=FileSystemLoader(template_dir))
        template = environment.get_template(template_file)

        rendered_template = template.render(ctxt)

        if self._ETC_DEFAULT.exists():
            self._ETC_DEFAULT.unlink()

        self._ETC_DEFAULT.write_text(rendered_template)

        # Clear cache dir after upgrade to avoid stale data
        self.setup_cache_dir()

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
            "-i"
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
