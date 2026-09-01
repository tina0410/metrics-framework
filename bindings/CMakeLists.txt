cmake_minimum_required(VERSION 3.20)
project(lsce_reference LANGUAGES CXX)
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang" OR
   NOT CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL 20 OR
   CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL 21)
  message(FATAL_ERROR "LSCE requires Clang 20; select it with CXX or CMAKE_CXX_COMPILER")
endif()
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
find_package(Python 3.10 COMPONENTS Interpreter Development.Module REQUIRED)
if(NOT Python_VERSION_MAJOR EQUAL 3 OR NOT Python_VERSION_MINOR EQUAL 10)
  message(FATAL_ERROR
    "LSCE requires Python 3.10.x; configure with the Python 3.10 environment")
endif()
execute_process(
  COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
  OUTPUT_VARIABLE nanobind_ROOT
  OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY
)
find_package(nanobind 2.9 CONFIG REQUIRED)
if(NOT LSCE_MODULE MATCHES "^_lsce_[a-f0-9]+$")
  message(FATAL_ERROR "LSCE_MODULE must be a unique _lsce_<hex> module name")
endif()
if(NOT EXISTS "${LSCE_GENERATED}/parameters.hpp" OR
   NOT EXISTS "${LSCE_GENERATED}/config.h")
  message(FATAL_ERROR "Generate LSCE parameters.hpp and config.h before configuring")
endif()
configure_file(module.cpp.in "${CMAKE_CURRENT_BINARY_DIR}/module.cpp" @ONLY)
nanobind_add_module(${LSCE_MODULE} NB_STATIC NOMINSIZE
  "${CMAKE_CURRENT_BINARY_DIR}/module.cpp"
  reference.cpp
)
target_include_directories(${LSCE_MODULE} PRIVATE
  "${LSCE_GENERATED}" "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/../BehaviorialVerification/include"
)
set_target_properties(${LSCE_MODULE} PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/module"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/module"
)
