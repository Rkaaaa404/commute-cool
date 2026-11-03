# AWS SAM custom build (BuildMethod: makefile in template.yaml).
# Runs inside the SAM build container (sam build --use-container) so wheels are Linux builds.
# uvicorn is not needed on Lambda (Mangum is the entry point), so it is filtered out.

build-ApiFunction:
	grep -v "^uvicorn" requirements-api.txt > /tmp/requirements-lambda.txt
	pip install --no-cache-dir -r /tmp/requirements-lambda.txt -t "$(ARTIFACTS_DIR)"
	cp -r api "$(ARTIFACTS_DIR)/api"
	find "$(ARTIFACTS_DIR)" -name __pycache__ -type d -prune -exec rm -rf {} +
