.PHONY: clone-firecracker

clone-firecracker:
	@if [ -d firecracker/.git ]; then \
		echo "firecracker repository already exists at ./firecracker"; \
	else \
		git clone https://github.com/firecracker-microvm/firecracker firecracker; \
	fi
