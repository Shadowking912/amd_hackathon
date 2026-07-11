# AMD Hackathon Track 1 — Smart Router
# Override any variable: `make build IMAGE=ghcr.io/me/router TAG=v2`

# ---- Configurable variables -------------------------------------------------------------
IMAGE     ?= shadowking9021/amd-hackathon
TAG       ?= track1_v2
PLATFORM  ?= linux/amd64
# main.py | variant_local_only.py | variant_self_consistency.py | variant_two_tier.py
ENTRYPOINT ?= main.py

# Model download overrides (passed through to download_model.sh)
REPO ?=
FILE ?=

IMG := $(IMAGE):$(TAG)

.PHONY: help model build push run test clean

help:
	@echo "Targets:"
	@echo "  make model                 Download the local GGUF (models/local.gguf)"
	@echo "  make build                 Build image $(IMG) for $(PLATFORM)"
	@echo "  make push                  Build and --push image $(IMG)"
	@echo "  make run                   Run container on practice_tasks.json locally"
	@echo "  make test                  Run the router directly (no Docker) on practice tasks"
	@echo "  make clean                 Remove local input/output + __pycache__"
	@echo ""
	@echo "Environment: Create .env file with FIREWORKS_API_KEY, FIREWORKS_BASE_URL, ALLOWED_MODELS"
	@echo "Vars: IMAGE=$(IMAGE) TAG=$(TAG) PLATFORM=$(PLATFORM) ENTRYPOINT=$(ENTRYPOINT)"

# Download the free local model into models/local.gguf.
model:
	REPO="$(REPO)" FILE="$(FILE)" ./download_model.sh

# Build for the judging platform. Depends on the model file existing.
build: models/local.gguf
	docker buildx build --platform $(PLATFORM) --build-arg ENTRYPOINT_FILE=$(ENTRYPOINT) \
		--tag $(IMG) --load .

# Build and push (public registry) — what you submit.
push: models/local.gguf
	docker buildx build --platform $(PLATFORM) --build-arg ENTRYPOINT_FILE=$(ENTRYPOINT) \
		--tag $(IMG) --push .

models/local.gguf:
	@echo "models/local.gguf missing — run 'make model' first (or delete the COPY line in Dockerfile)."
	@exit 1

# Run the built image locally against the practice tasks, mirroring the harness mounts.
run:
	mkdir -p input output
	cp practice_tasks.json input/tasks.json
	bash -c 'set -a; [ -f .env ] && . .env; set +a; docker run --rm -e FIREWORKS_API_KEY="$$FIREWORKS_API_KEY" -e FIREWORKS_BASE_URL="$$FIREWORKS_BASE_URL" -e ALLOWED_MODELS="$$ALLOWED_MODELS" -v "$(PWD)/input:/input" -v "$(PWD)/output:/output" $(IMG)'
	@python3 -m json.tool output/results.json > /dev/null && echo "results.json is valid JSON"

# Fast local smoke test without Docker (uses whatever env you have set).
test:
	mkdir -p input output
	cp practice_tasks.json input/tasks.json
	bash -c 'set -a; [ -f .env ] && . .env; set +a; INPUT_PATH=input/tasks.json OUTPUT_PATH=output/results.json python3 $(ENTRYPOINT)'
	@python3 -m json.tool output/results.json > /dev/null && echo "results.json is valid JSON"

clean:
	rm -rf input output __pycache__
