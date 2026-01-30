BINARY_NAME=smon
SRC=src/main.py

.PHONY: all build deploy clean

# "all" now triggers a clean build by default
all: clean build

build:
	uv sync
	uv run pyinstaller --onefile --name $(BINARY_NAME) $(SRC)

deploy: all
	mkdir -p ~/.local/bin
	cp dist/$(BINARY_NAME) ~/.local/bin/$(BINARY_NAME)
	@echo "------------------------------------------------"
	@echo "Successfully cleaned, built, and deployed to ~/.local/bin/$(BINARY_NAME)"

clean:
	rm -rf build dist *.spec
	@echo "Cleaned up old build artifacts."