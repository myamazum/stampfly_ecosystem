/**
 * @file cmd_comm.cpp
 * @brief Communication commands (comm, pair, unpair)
 *
 * 通信コマンド
 */

#include "console.hpp"
#include "controller_comm.hpp"
#include "control_arbiter.hpp"
#include "udp_server.hpp"
#include "esp_console.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include <cstring>
#include <cstdlib>

// External references
// 外部参照
extern stampfly::ControllerComm* g_comm_ptr;

// Shared control handler (defined in main.cpp)
// 共有制御ハンドラ（main.cppで定義）
extern void handleControlInput(uint16_t throttle, uint16_t roll, uint16_t pitch,
                               uint16_t yaw, uint8_t flags);

// NVS keys
static const char* NVS_NAMESPACE_CLI = "stampfly_cli";
static const char* NVS_KEY_COMM_MODE = "comm_mode";

namespace stampfly {

// =============================================================================
// NVS Helper Functions
// =============================================================================

// Returns: 0 = ESP-NOW, 1 = UDP, -1 = not found/error
static int loadCommModeFromNVS()
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open(NVS_NAMESPACE_CLI, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return -1;  // NVS not initialized or namespace not found
    }

    uint8_t mode = 0;
    ret = nvs_get_u8(handle, NVS_KEY_COMM_MODE, &mode);
    nvs_close(handle);

    if (ret != ESP_OK) {
        return -1;  // Key not found
    }
    return static_cast<int>(mode);
}

static esp_err_t saveCommModeToNVS(uint8_t mode)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open(NVS_NAMESPACE_CLI, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        return ret;
    }

    ret = nvs_set_u8(handle, NVS_KEY_COMM_MODE, mode);
    if (ret == ESP_OK) {
        ret = nvs_commit(handle);
    }

    nvs_close(handle);
    return ret;
}

// =============================================================================
// comm command
// =============================================================================

static int cmd_comm(int argc, char** argv)
{
    auto& console = Console::getInstance();
    auto& arbiter = ControlArbiter::getInstance();
    auto& udp_server = UDPServer::getInstance();

    if (argc < 2) {
        console.print("=== Communication Status ===\r\n");

        // Current mode
        CommMode mode = arbiter.getCommMode();
        console.print("Mode: %s\r\n", ControlArbiter::getCommModeName(mode));

        // ESP-NOW status
        if (g_comm_ptr != nullptr) {
            console.print("\r\nESP-NOW:\r\n");
            console.print("  Paired: %s\r\n", g_comm_ptr->isPaired() ? "yes" : "no");
            console.print("  Connected: %s\r\n", g_comm_ptr->isConnected() ? "yes" : "no");
            console.print("  Channel: %d\r\n", g_comm_ptr->getChannel());
        }

        // UDP status
        console.print("\r\nUDP:\r\n");
        console.print("  Running: %s\r\n", udp_server.isRunning() ? "yes" : "no");
        console.print("  Clients: %d\r\n", udp_server.getClientCount());
        console.print("  RX count: %lu\r\n", udp_server.getRxCount());
        console.print("  TX count: %lu\r\n", udp_server.getTxCount());
        console.print("  Errors: %lu\r\n", udp_server.getErrorCount());

        // Control Arbiter stats
        console.print("\r\nControl Arbiter:\r\n");
        console.print("  ESP-NOW packets: %lu\r\n", arbiter.getESPNOWCount());
        console.print("  UDP packets: %lu\r\n", arbiter.getUDPCount());
        console.print("  WebSocket packets: %lu\r\n", arbiter.getWebSocketCount());
        console.print("  Active control: %s\r\n", arbiter.hasActiveControl() ? "yes" : "no");

        console.print("\r\nUsage:\r\n");
        console.print("  comm espnow    - Switch to ESP-NOW mode\r\n");
        console.print("  comm udp       - Switch to UDP mode\r\n");
        console.print("  comm status    - Show this status\r\n");
        return 0;
    }

    const char* cmd = argv[1];

    if (strcmp(cmd, "espnow") == 0) {
        arbiter.setCommMode(CommMode::ESPNOW);
        console.print("Communication mode set to ESP-NOW\r\n");

        if (udp_server.isRunning()) {
            udp_server.stop();
            console.print("UDP server stopped\r\n");
        }

        saveCommModeToNVS(0);  // 0 = ESP-NOW
        console.print("Mode saved to NVS\r\n");
    } else if (strcmp(cmd, "udp") == 0) {
        if (!udp_server.isRunning()) {
            esp_err_t ret = udp_server.init();
            if (ret != ESP_OK) {
                console.print("Failed to init UDP server: %s\r\n", esp_err_to_name(ret));
                return 1;
            }

            ret = udp_server.start();
            if (ret != ESP_OK) {
                console.print("Failed to start UDP server: %s\r\n", esp_err_to_name(ret));
                return 1;
            }
            console.print("UDP server started on port %d\r\n", 8888);
        }

        // Set callback
        udp_server.setControlCallback([](const udp::ControlPacket& pkt, const SockAddrIn*) {
            auto& arb = ControlArbiter::getInstance();
            arb.updateFromUDP(pkt.throttle, pkt.roll, pkt.pitch, pkt.yaw, pkt.flags);
            handleControlInput(pkt.throttle, pkt.roll, pkt.pitch, pkt.yaw, pkt.flags);
        });

        arbiter.setCommMode(CommMode::UDP);
        console.print("Communication mode set to UDP\r\n");
        console.print("WiFi AP SSID: StampFly\r\n");
        console.print("Vehicle IP: 192.168.4.1\r\n");

        saveCommModeToNVS(1);  // 1 = UDP
        console.print("Mode saved to NVS\r\n");
    } else if (strcmp(cmd, "status") == 0) {
        // Re-call with argc=1 to show status
        char* empty_argv[] = { argv[0] };
        return cmd_comm(1, empty_argv);
    } else {
        console.print("Unknown command: %s\r\n", cmd);
        return 1;
    }

    return 0;
}

// =============================================================================
// pair command
// =============================================================================

static int cmd_pair(int argc, char** argv)
{
    auto& console = Console::getInstance();

    if (g_comm_ptr == nullptr) {
        console.print("ControllerComm not available\r\n");
        return 1;
    }

    if (argc < 2) {
        console.print("ESP-NOW Pairing Status:\r\n");
        console.print("  Initialized: %s\r\n", g_comm_ptr->isInitialized() ? "yes" : "no");
        console.print("  Channel: %d\r\n", g_comm_ptr->getChannel());
        console.print("  Paired: %s\r\n", g_comm_ptr->isPaired() ? "yes" : "no");
        console.print("  Connected: %s\r\n", g_comm_ptr->isConnected() ? "yes" : "no");
        console.print("  Pairing mode: %s\r\n", g_comm_ptr->isPairingMode() ? "active" : "inactive");
        console.print("\r\nUsage:\r\n");
        console.print("  pair start      - Enter pairing mode\r\n");
        console.print("  pair stop       - Exit pairing mode\r\n");
        console.print("  pair channel <n>- Set WiFi channel (1-13)\r\n");
        return 0;
    }

    const char* cmd = argv[1];

    if (strcmp(cmd, "start") == 0) {
        if (g_comm_ptr->isPairingMode()) {
            console.print("Already in pairing mode\r\n");
            return 0;
        }
        console.print("Entering pairing mode on channel %d...\r\n", g_comm_ptr->getChannel());
        console.print("Send control packet from controller to complete pairing.\r\n");
        g_comm_ptr->enterPairingMode();
    } else if (strcmp(cmd, "stop") == 0) {
        if (!g_comm_ptr->isPairingMode()) {
            console.print("Not in pairing mode\r\n");
            return 0;
        }
        console.print("Exiting pairing mode\r\n");
        g_comm_ptr->exitPairingMode();
    } else if (strcmp(cmd, "channel") == 0) {
        if (argc < 3) {
            console.print("Current channel: %d\r\n", g_comm_ptr->getChannel());
            console.print("Usage: pair channel <1-13>\r\n");
            return 0;
        }
        int channel = atoi(argv[2]);
        if (channel < 1 || channel > 13) {
            console.print("Invalid channel. Use 1-13.\r\n");
            return 1;
        }
        // Set channel and save to NVS
        esp_err_t ret = g_comm_ptr->setChannel(channel, true);
        if (ret == ESP_OK) {
            console.print("WiFi channel set to %d (saved to NVS)\r\n", channel);
        } else {
            console.print("Failed to set channel: %s\r\n", esp_err_to_name(ret));
            return 1;
        }
    } else {
        console.print("Unknown subcommand: %s\r\n", cmd);
        return 1;
    }

    return 0;
}

// =============================================================================
// unpair command
// =============================================================================

static int cmd_unpair(int argc, char** argv)
{
    auto& console = Console::getInstance();

    if (g_comm_ptr == nullptr) {
        console.print("ControllerComm not available\r\n");
        return 1;
    }

    if (!g_comm_ptr->isPaired()) {
        console.print("Not paired to any controller\r\n");
        return 0;
    }

    console.print("Clearing pairing information...\r\n");
    esp_err_t ret = g_comm_ptr->clearPairingFromNVS();
    if (ret == ESP_OK) {
        console.print("Pairing cleared successfully\r\n");
    } else {
        console.print("Failed to clear pairing: %s\r\n", esp_err_to_name(ret));
        return 1;
    }

    return 0;
}

// =============================================================================
// Command Registration
// =============================================================================

void register_comm_commands()
{
    // Load comm mode from NVS at startup
    // 起動時に NVS から通信モードを読み込む
    int saved_mode = loadCommModeFromNVS();
    if (saved_mode >= 0) {
        auto& arbiter = ControlArbiter::getInstance();
        CommMode mode = (saved_mode == 1) ? CommMode::UDP : CommMode::ESPNOW;
        arbiter.setCommMode(mode);
        ESP_LOGI("CommCmds", "Comm mode loaded from NVS: %s",
                 ControlArbiter::getCommModeName(mode));
    }

    // comm
    const esp_console_cmd_t comm_cmd = {
        .command = "comm",
        .help = "Comm mode [espnow|udp|status]",
        .hint = NULL,
        .func = &cmd_comm,
        .argtable = NULL,
    };
    esp_console_cmd_register(&comm_cmd);

    // pair
    const esp_console_cmd_t pair_cmd = {
        .command = "pair",
        .help = "Pairing control [start|stop|channel]",
        .hint = NULL,
        .func = &cmd_pair,
        .argtable = NULL,
    };
    esp_console_cmd_register(&pair_cmd);

    // unpair
    const esp_console_cmd_t unpair_cmd = {
        .command = "unpair",
        .help = "Clear pairing",
        .hint = NULL,
        .func = &cmd_unpair,
        .argtable = NULL,
    };
    esp_console_cmd_register(&unpair_cmd);
}

}  // namespace stampfly
