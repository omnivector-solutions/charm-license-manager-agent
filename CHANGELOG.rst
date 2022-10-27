==========
Change Log
==========

This file keeps track of all notable changes to the License Manager Agent Charm.

Unreleased
----------
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