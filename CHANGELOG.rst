=========
Changelog
=========

This file keeps track of all notable changes to the License Manager Agent Charm.

Unreleased
----------

- fix command to reload systemd settings when installing
- add config options to set the path to rlmutil and lmutil
- add config options to set the path for ls-dyna
- add config options to set the path for lm-x
- add config option to define if reconciliation should run during Prolog/Epilog execution
- add config option `timeout-interval` to terminate the service in case it hangs
- add support to Fluentbit log forwarding
- change OIDC configurations to support any kind of OIDC provider
- change package provider to PyPI.org

0.0.1 - 2021-11-10
------------------

- initital release