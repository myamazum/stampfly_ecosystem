# Workshop main component
# Compiles workshop-specific files and reuses vehicle sensor/peripheral tasks

set(VEHICLE_TASKS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../vehicle/main/tasks")
set(VEHICLE_MAIN_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../vehicle/main")

idf_component_register(
    SRCS
        "workshop_main.cpp"
        "workshop_globals.cpp"
        "workshop_task.cpp"
        "workshop_api.cpp"
        "user_code.cpp"
        # Reuse vehicle sensor/peripheral tasks (compiled from vehicle source)
        "${VEHICLE_TASKS_DIR}/imu_task.cpp"
        "${VEHICLE_TASKS_DIR}/optflow_task.cpp"
        "${VEHICLE_TASKS_DIR}/mag_task.cpp"
        "${VEHICLE_TASKS_DIR}/baro_task.cpp"
        "${VEHICLE_TASKS_DIR}/tof_task.cpp"
        "${VEHICLE_TASKS_DIR}/power_task.cpp"
        "${VEHICLE_TASKS_DIR}/led_task.cpp"
        "${VEHICLE_TASKS_DIR}/button_task.cpp"
        "${VEHICLE_TASKS_DIR}/comm_task.cpp"
        "${VEHICLE_TASKS_DIR}/cli_task.cpp"
        "${VEHICLE_TASKS_DIR}/telemetry_task.cpp"
        # Reuse vehicle init (shared initialization code)
        "${VEHICLE_MAIN_DIR}/init.cpp"
    INCLUDE_DIRS
        "."
        "${VEHICLE_MAIN_DIR}"
        "${VEHICLE_MAIN_DIR}/tasks"
    REQUIRES
        esp_timer
        sf_hal_bmi270
        sf_hal_vl53l3cx
        sf_hal_pmw3901
        sf_hal_bmm150
        sf_hal_bmp280
        sf_hal_power
        sf_hal_motor
        sf_hal_led
        sf_hal_buzzer
        sf_hal_button
        sf_algo_filter
        sf_algo_eskf
        sf_algo_fusion
        sf_algo_pid
        sf_algo_control
        sf_svc_health
        sf_svc_state
        sf_svc_comm
        sf_svc_console
        sf_svc_telemetry
        sf_svc_wifi_cli
        sf_svc_serial_cli
        sf_svc_led
        sf_svc_flight_command
)
