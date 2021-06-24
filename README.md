# charm-license-manager-agent


# Usage
Follow the steps below to get started.

### Build the charm

Running the following command will produce a .charm file, `license-manager-agent.charm`
```bash
charmcraft build
```

### Create the license-manager-agent charm config

`license-manager-agent.yaml`

```yaml
license-manager-agent:
  log-level: DEBUG
  stat-interval: 60
  jwt-key: "your-jwt-key-to-access-the-licnese-manager-backend"
  pypi-url: "https://pypicloud.omnivector.solutions"
  pypi-username: "<pypi-username>"
  pypi-password: "<pypi-password>"
  domain: "<domain>"
```

### Deploy the charm
Using the built charm and the defined config, run the command to deploy the charm.
```bash
juju deploy ./license-manager-agent.charm \
    --config ./license-manager-agent.yaml \
    --series centos7
```

### Change configuration
Modify charm configuration.
```bash
juju config license-manager-agent jwt-key=somenewvalue
```
Running the above command will tell the charm to reconfigure and restart license-manager-agent.

