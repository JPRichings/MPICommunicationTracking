cmake_minimum_required(VERSION 3.10)

project(Pyrite VERSION 1.0 LANGUAGES C)

# Includes standard variables like CMAKE_INSTALL_BINDIR and CMAKE_INSTALL_LIBDIR
include(GNUInstallDirs)

# Find the MPI library system-wide for C
find_package(MPI REQUIRED COMPONENTS C)

include(CTest)
enable_testing()

add_subdirectory(src)

if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

add_subdirectory(examples)

# =========================================================================
# Install Python Tools
# =========================================================================
# Copies everything inside tools/ to bin/ and keeps them executable
install(DIRECTORY tools/
    DESTINATION ${CMAKE_INSTALL_BINDIR}
    USE_SOURCE_PERMISSIONS
    FILES_MATCHING PATTERN "*.py" # Optional: only grab .py files
)
