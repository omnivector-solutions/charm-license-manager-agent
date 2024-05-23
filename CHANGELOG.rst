==========
Change Log
==========

This file keeps track of all notable changes to the License Manager Agent Charm.

Unreleased
----------
- Include stat interval env var in the agent's configuration

1.1.3 - 2023-12-11
------------------
- Drop support for CentOS 8
- Installed Python 3.12 to run the agent

1.1.2 - 2023-08-08
------------------
* Add support for Rocky Linux and Ubuntu Jammy

1.1.1 - 2023-05-23
------------------
* Set ops to version 1.3.0

1.1.0 - 2023-03-07
------------------
* Add support to use Slurm reservations by setting an user and account

1.0.0 - 2022-12-15
------------------
* Add an action to show the version of license-manager-agent. 
* Fix command to reload systemd settings when installing
* Add config options to set the path to rlmutil (RLM binary) and lmutil (FlexLM binary)
* Add config options to set the path for lsdyna (LS-Dyna binary)
* Add config options to set the path for lmxendutil (LM-X binary)
* Add config option to define if reconciliation should run during Prolog/Epilog execution
* Add config option `timeout_interval` to terminate the service in case it hangs
* Add support to Fluentbit log forwarding
* Change OIDC configurations to support any kind of OIDC provider
* Change package provider to PyPI.org
* Add config options to set the path for olixtool (OLicense binary)

0.0.1 - 2021-11-10
------------------
* Initital release
