# StampFly Workshop Skeleton
# ESP-IDF v5.4 Project
#
# Reuses vehicle components via EXTRA_COMPONENT_DIRS
# vehicle コンポーネントを再利用

cmake_minimum_required(VERSION 3.16)

# Include vehicle components and common shared components
# vehicle コンポーネントと共通コンポーネントの両方を含める
set(EXTRA_COMPONENT_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/../vehicle/components
    ${CMAKE_CURRENT_SOURCE_DIR}/../common
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(stampfly_workshop)
