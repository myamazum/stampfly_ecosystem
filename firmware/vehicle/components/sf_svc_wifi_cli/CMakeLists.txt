idf_component_register(
    SRCS "wifi_cli.cpp"
    INCLUDE_DIRS "include"
    REQUIRES esp_wifi lwip freertos sf_svc_cli
)
