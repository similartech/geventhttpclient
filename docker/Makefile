script_dir=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

IMAGE_NAME="docker-st-py-geventhttpclient"

install_dev:
	cd .. ; docker build -t ${IMAGE_NAME}-dev --no-cache -f docker/dev/Dockerfile .

.PHONY: dock local_dock install_dev
