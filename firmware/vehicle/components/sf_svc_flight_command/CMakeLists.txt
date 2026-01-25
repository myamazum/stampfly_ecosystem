idf_component_register(
    SRCS
        "flight_command.cpp"
        "command_queue.cpp"
    INCLUDE_DIRS
        "include"
    REQUIRES
        freertos
        esp_timer
        sf_svc_state
        sf_svc_control_arbiter
        sf_algo_fusion
)

# Access to main/ directory for globals.hpp
# main/ディレクトリへのアクセス（globals.hpp用）
target_include_directories(${COMPONENT_LIB} PRIVATE ${CMAKE_SOURCE_DIR}/main)
