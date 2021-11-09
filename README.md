# charm-license-manager-agent


# Usage
Follow the steps below to get started.

### Build the charm

Running the following command will produce a `.charm` file,
`license-manager-agent_ubuntu-20.04-amd64_centos-7-amd64.charm`:
```bash
$ charmcraft pack
```

### Create the license-manager-agent charm config

`license-manager-agent.yaml`

```yaml
license-manager-agent:
  log-level: DEBUG
  stat-interval: 60
  jwt-key: "your-jwt-key-to-access-the-license-manager-backend"
  pypi-url: "https://pypicloud.omnivector.solutions"
  pypi-username: "<pypi-username>"
  pypi-password: "<pypi-password>"
  sentry-dsn: "https://sentrydsn.com:123"
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

