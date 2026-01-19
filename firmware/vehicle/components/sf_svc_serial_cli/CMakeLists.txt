idf_component_register(
    SRCS "serial_cli.cpp"
    INCLUDE_DIRS "include"
    REQUIRES
        console
        freertos
        sf_svc_console
        sf_lib_line_editor
)
