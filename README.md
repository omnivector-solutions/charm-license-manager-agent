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
  jwt-key: "your-jwt-key-to-access-the-licnese-manager-backend"
  service-addrs: "flexlm:127.0.0.1:2345"
  license-server-features: |
    - features:
      - TESTFEATURE
      license_server_type: flexlm
  license-manager-backend-base-url: "https://license-manager-bdx-us-west-2.omnivector.solutions"
  pypi-url: "https://pypicloud.omnivector.solutions/simple/license-manager"
  pypi-username: "<pypi-username>"
  pypi-password: "<pypi-password>"
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


#### Todo
* checks for successfull installation of license-manager and its dependencies
* support prolog and epilog wrapper commands
* add the log dir to the list of vars defined in etc default
