# ==============================================================================
# Minecraft Desktop — Universal Edition Makefile
# ==============================================================================
# ponytail: [build: basic cross-platform Makefile] -> [Ninja / Meson meta-build generator]
# ponytail: [dependencies: system OS headers] -> [vendored C99 amalgamation source trees]

CC ?= gcc
CFLAGS ?= -std=c99 -Wall -Wextra -O2 -Isrc
LDFLAGS ?=

# OS-specific link flags and directory commands
ifeq ($(OS),Windows_NT)
    WIN_LIBS = -lopengl32 -lgdi32 -lwinmm -luser32 -lshell32
    BIN_EXT = .exe
    MKDIR = if not exist build mkdir build
    RM = rmdir /s /q build 2>nul || true
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        WIN_LIBS = -lm -framework IOKit -framework Cocoa -framework OpenGL -framework CoreVideo
    else
        WIN_LIBS = -lGL -lm -lpthread -ldl -lrt -lX11
    endif
    BIN_EXT =
    MKDIR = mkdir -p build
    RM = rm -rf build
endif

# Core subsystem sources (all 6 subsystems)
SRCS_CORE = \
    src/core/runtime.c \
    src/platform/platform_desktop.c \
    src/world/terrain.c \
    src/world/chunk.c \
    src/world/mesher.c \
    src/gameplay/physics.c \
    src/gameplay/raycast.c \
    src/gameplay/interaction.c \
    src/gameplay/inventory.c \
    src/assets/assets.c \
    src/audio/synthesizer.c

SRCS_MAIN = src/main.c

TARGET_HEADLESS = build/minecraft_headless$(BIN_EXT)
TARGET_APP = build/minecraft$(BIN_EXT)

.PHONY: all headless app test test-py clean

all: headless

headless: $(TARGET_HEADLESS)

$(TARGET_HEADLESS): $(SRCS_CORE) $(SRCS_MAIN)
	@$(MKDIR)
	$(CC) $(CFLAGS) -DHEADLESS_ONLY $^ -o $@ $(LDFLAGS) $(WIN_LIBS)

# Full target with Raylib (if raylib is installed/provided in system)
app: $(TARGET_APP)

$(TARGET_APP): $(SRCS_CORE) $(SRCS_MAIN)
	@$(MKDIR)
	$(CC) $(CFLAGS) -DHAVE_RAYLIB $^ -o $@ $(LDFLAGS) -lraylib $(WIN_LIBS)

test: $(TARGET_HEADLESS)
	$(TARGET_HEADLESS) --test-m1

test-py:
	python tests/test_runner.py
	python -m unittest discover -s tests -p "test_*.py"

clean:
	@$(RM)
