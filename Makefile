.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: lint
lint: ## Run linter
	flake8 src/

version: ## Create/update version file
	@git describe --dirty --tags > version

.PHONY: clean
clean: ## Remove build dirs, temp files, and charms
	rm -rf venv/
	rm -rf build
	rm -rf version
	find . -name "*.charm" -delete

.PHONY: charm
charm: version ## Pack the charm
	@charmcraft pack
