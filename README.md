# License Manager Agent Charm


## Usage

Follow the steps below to get started.

### Build the charm

Running the following command will produce a `.charm` file,
`license-manager-agent.charm`:
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

Create a text file `license-manager-agent.yaml` with this content:

```yaml
license-manager-agent:
  backend-base-url: "http://<url-pointing-to-the-license-manager-backend>"
  stat-interval: 60
  lmutil-path: "<path-to-lmutil>"
  rlmutil-path: "<path-to-rlmutil>"
  lsdyna-path: "<path-to-lstc_qrun>"
  lmxendutil-path: "<path-to-lmxendutil>"
  olixtool-path: "<path-to-olixtool>"
  dslicsrv-path: "<path-to-dslicsrv>"
  oidc-domain: "<domain-collected-from-oidc>"
  oidc-client-id: "<client-id-for-oidc-app>"
  oidc-client-secret: "<client-secret-for-oidc-app>"
  log-level: "DEBUG"
  deploy-env: "LOCAL" # can be STAGING or PROD as well
```

### Deploy the charm

Using the built charm and the defined config, run the following command to
deploy the charm:

```bash
$ juju deploy ./license-manager-agent.charm \
              --config ./license-manager-agent.yaml \
              --series jammy
$ juju relate license-manager-agent:juju-info slurmctld
$ juju relate license-manager-agent:prolog-epilog slurmctld
```

### Release the charm
To make a new release of the License Manager Agent Charm:

1. Update the CHANGELOG file, moving the changes under the Unreleased section to the new version section. Always keep an `Unreleased` section at the top.
2. Create a new commit with the title `Release x.y.z`
3. Create a new annotated Git tag, adding a summary of the changes in the tag message:
```bash
$ git tag --annotate --sign x.y.z
```
4. Push the new tag to GitHub:
```bash
$ git push --tags
```

### Change configuration

To modify the charm configuration after it was deployed, use the `juju config` command. For example:
```bash
juju config license-manager-agent backend-base-url=somenewvalue
```

If you wish to prevent Prolog/Epilog scripts from triggering a forced reconciliation, run:
```bash
juju config license manager-agent use-reconcile-in-prolog-epilog=false
```

Running the `juju config` command will tell the charm to reconfigure and restart license-manager-agent.
