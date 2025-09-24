cmake_minimum_required(VERSION 3.24)
project(hft-core VERSION 0.1.0 LANGUAGES CXX)

option(HFTCORE_BUILD_APPS "Build example applications" ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_library(hftcore
    src/order_book.cpp
    src/order_router.cpp
    src/shard.cpp
    src/affinity.cpp
    src/ingress_coordinator.cpp
    src/matching_engine.cpp
    src/replay/dbn_reader.cpp
    src/replay/dbn_local_source.cpp
    src/replay/replay_driver.cpp
    src/backtester.cpp
)

target_include_directories(hftcore
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_definitions(hftcore PRIVATE HFTCORE_VERSION="${PROJECT_VERSION}")

# Databento C++ client (for DBN decoding)
include(FetchContent)
find_package(OpenSSL REQUIRED)

FetchContent_Declare(
    databento
    GIT_REPOSITORY https://github.com/databento/databento-cpp
    GIT_TAG HEAD
)
FetchContent_MakeAvailable(databento)

target_link_libraries(hftcore PRIVATE databento::databento)

if(HFTCORE_BUILD_APPS)
    add_subdirectory(apps/replay_sim)
    add_subdirectory(apps/random_sim)
    add_subdirectory(apps/backtest_sim)
endif()

