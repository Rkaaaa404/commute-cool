# AWS SAM custom build (BuildMethod: makefile, CodeUri: api in template.yaml).
# Runs inside the SAM build container (sam build --use-container) so wheels are Linux builds.
# uvicorn is not needed on Lambda (Mangum is the entry point), so it is filtered out.

build-ApiFunction:
	grep -v "^uvicorn" requirements.txt > /tmp/requirements-lambda.txt
	pip install --no-cache-dir -r /tmp/requirements-lambda.txt -t "$(ARTIFACTS_DIR)"
	mkdir -p "$(ARTIFACTS_DIR)/api"
	cp -r *.py models routes "$(ARTIFACTS_DIR)/api/"
	find "$(ARTIFACTS_DIR)" -name __pycache__ -type d -prune -exec rm -rf {} +
