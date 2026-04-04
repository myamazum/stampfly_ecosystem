cmake_minimum_required(VERSION 3.14)
project(eskf_test)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

# ESP-IDF types stub
add_library(esp_stubs INTERFACE)
target_include_directories(esp_stubs INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/stubs)

# Math library (header-only)
add_library(sf_algo_math INTERFACE)
target_include_directories(sf_algo_math INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/sf_algo_math/include
)

# ESKF_V2 library
add_library(sf_algo_eskf
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/sf_algo_eskf/eskf_v2.cpp
)
target_include_directories(sf_algo_eskf PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/sf_algo_eskf/include
    ${CMAKE_CURRENT_SOURCE_DIR}
)
target_include_directories(sf_algo_eskf BEFORE PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/stubs)
target_link_libraries(sf_algo_eskf PUBLIC sf_algo_math)

# Unit test executable
add_executable(eskf_v2_test eskf_v2_test.cpp)
target_link_libraries(eskf_v2_test PRIVATE sf_algo_eskf)
