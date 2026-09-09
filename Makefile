.PHONY: help setup install dmg test test-dashboard check up down logs status urls plausible fooocus dashboard
MODULE ?= dashboard
help:
	@echo "make setup | test | test-dashboard | check | dmg | dashboard | plausible | fooocus"
	@echo "pt pipeline <URL-or-file> | pt services up automation | pt services up design"
setup install:
	bash scripts/install-cli.sh
dmg:
	bash macos/build-dmg.sh
test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
test-dashboard:
	node --test tests/dashboard.test.cjs
check:
	python3 scripts/check.py
up:
	./bin/pt services up $(MODULE)
dashboard:
	./bin/pt dashboard
down:
	./bin/pt services down $(MODULE)
logs:
	./bin/pt services logs $(MODULE)
status:
	./bin/pt services status
urls:
	./bin/pt urls
plausible:
	bash scripts/setup-plausible.sh
fooocus:
	bash scripts/setup-fooocus.sh
