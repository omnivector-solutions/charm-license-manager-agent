# License Manager agent Charm


# Usage

Follow the steps below to get started.

### Build the charm

Running the following command will produce a `.charm` file,
`license-manager-agent_ubuntu-20.04-amd64_centos-7-amd64.charm`:
```bash
$ make charm
```

### Linter

The linter can be invoked with:

```bash
$ make lint
```

This requires `flake8` and `flake8-docstrings`. Make sure to have them
available, either in a virtual environment or via a native package.

### Create the license-manager-agent charm config

`license-manager-agent.yaml`

```yaml
license-manager-agent:
  log-level: DEBUG
  stat-interval: 60
  jwt-key: "your.jwt.key"
  pypi-url: "https://pypicloud.omnivector.solutions"
  pypi-username: "<pypi-username>"
  pypi-password: "<pypi-password>"
  license-manager-backend-base-url: "http://<url-pointing-to-the-license-manager-backend>"
```

### Deploy the charm
Using the built charm and the defined config, run the command to deploy the charm.
```bash
juju deploy ./license-manager-agent_ubuntu-20.04-amd64_centos-7-amd64.charm \
    --config ./license-manager-agent.yaml \
    --series centos7

juju relate license-manager-agent:juju-info slurmctld
```

### Change configuration
Modify charm configuration.
```bash
juju config license-manager-agent jwt-key=somenewvalue
```
Running the above command will tell the charm to reconfigure and restart license-manager-agent.

