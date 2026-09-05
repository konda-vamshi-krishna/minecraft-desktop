# ==============================================================================
# CMakeLists.txt — Minecraft Desktop Universal Edition
# ==============================================================================
# ponytail: [build: single cmake file for all platforms] -> [modular cmake targets with presets]
# ponytail: [graphics: headless standalone executable] -> [dynamic backend selection via Glad/GLFW]

cmake_minimum_required(VERSION 3.16)
project(minecraft_desktop C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Global include search paths
include_directories(src)

# Core subsystem source files across all 6 subsystems
set(CORE_SOURCES
    src/core/runtime.c
    src/platform/platform_desktop.c
    src/world/terrain.c
    src/world/chunk.c
    src/world/mesher.c
    src/gameplay/physics.c
    src/gameplay/raycast.c
    src/gameplay/interaction.c
    src/gameplay/inventory.c
    src/assets/assets.c
    src/audio/synthesizer.c
)

# Compiler warnings and optimization flags
if(MSVC)
    add_compile_options(/W4 /O2)
else()
    add_compile_options(-Wall -Wextra -O2)
endif()

# OS-specific platform libraries
if(WIN32)
    set(PLATFORM_LIBS winmm)
elseif(UNIX AND NOT APPLE)
    set(PLATFORM_LIBS m pthread dl rt)
elseif(APPLE)
    find_library(COCOA_FRAMEWORK Cocoa)
    find_library(IOKIT_FRAMEWORK IOKit)
    find_library(OPENGL_FRAMEWORK OpenGL)
    find_library(COREVIDEO_FRAMEWORK CoreVideo)
    set(PLATFORM_LIBS m ${COCOA_FRAMEWORK} ${IOKIT_FRAMEWORK} ${OPENGL_FRAMEWORK} ${COREVIDEO_FRAMEWORK})
endif()

# Headless standalone target (zero external graphics dependencies)
add_executable(minecraft_headless
    ${CORE_SOURCES}
    src/main.c
)
target_include_directories(minecraft_headless PRIVATE src)
target_compile_definitions(minecraft_headless PRIVATE HEADLESS_ONLY)
target_link_libraries(minecraft_headless PRIVATE ${PLATFORM_LIBS})

# Optional Raylib Desktop Application Target (if Raylib is installed in system)
find_package(raylib QUIET)
if(raylib_FOUND)
    add_executable(minecraft
        ${CORE_SOURCES}
        src/main.c
    )
    target_include_directories(minecraft PRIVATE src)
    target_compile_definitions(minecraft PRIVATE HAVE_RAYLIB)
    target_link_libraries(minecraft PRIVATE raylib ${PLATFORM_LIBS})
else()
    message(STATUS "Raylib not found in system package registry. Standalone headless target active.")
endif()

# Enable automated testing via CTest
enable_testing()
add_test(NAME TestM1 COMMAND minecraft_headless --test-m1)

find_package(Python3 QUIET COMPONENTS Interpreter)
if(Python3_FOUND)
    add_test(NAME TestPythonOracle COMMAND ${Python3_EXECUTABLE} tests/test_runner.py)
    add_test(NAME TestPythonSuites COMMAND ${Python3_EXECUTABLE} -m unittest discover -s tests -p "test_*.py")
endif()
