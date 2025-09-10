cmake_minimum_required(VERSION 3.20)
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
    src/replay/replay_driver.cpp
)

target_include_directories(hftcore
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_definitions(hftcore PRIVATE HFTCORE_VERSION=\"${PROJECT_VERSION}\")

if(HFTCORE_BUILD_APPS)
    add_subdirectory(apps/replay_sim)
    add_subdirectory(apps/random_sim)
endif()

install(TARGETS hftcore EXPORT hftcoreTargets
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(DIRECTORY include/ DESTINATION include)
export(EXPORT hftcoreTargets FILE ${CMAKE_CURRENT_BINARY_DIR}/hftcoreTargets.cmake)

