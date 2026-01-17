# StampFly UDP Client Component
# UDP通信クライアントコンポーネント

idf_component_register(
    SRCS
        "udp_client.cpp"
    INCLUDE_DIRS
        "include"
    REQUIRES
        protocol
        lwip
        freertos
        esp_common
        esp_wifi
        esp_event
        esp_netif
        log
)
