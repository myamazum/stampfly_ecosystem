/**
 * @file cmd_flight.cpp
 * @brief Flight command CLI handlers
 *        飛行コマンドCLIハンドラ
 */

#include "console.hpp"
#include "flight_command.hpp"
#include <cstdlib>
#include <cstring>

using namespace stampfly;

// Jump command: jump [altitude_m] [hover_sec]
// ジャンプコマンド: jump [高度_m] [ホバリング_秒]
static int cmd_jump(int argc, char** argv) {
    auto& console = Console::getInstance();
    auto& flight = FlightCommandService::getInstance();

    if (!flight.canExecute()) {
        console.print("Error: Cannot execute. Check landing/calibration status.\r\n");
        return 1;
    }

    if (flight.isRunning()) {
        console.print("Error: Another command is running. Use 'flight cancel' first.\r\n");
        return 1;
    }

    float altitude = 0.15f;  // Default 0.15m (15cm)
    if (argc >= 2) {
        altitude = atof(argv[1]);
        if (altitude < 0.1f || altitude > 2.0f) {
            console.print("Error: Altitude must be 0.1-2.0 [m]\r\n");
            return 1;
        }
    }

    float hover_duration = 0.5f;  // Default 0.5s
    if (argc >= 3) {
        hover_duration = atof(argv[2]);
        if (hover_duration < 0.1f || hover_duration > 10.0f) {
            console.print("Error: Hover duration must be 0.1-10.0 [s]\r\n");
            return 1;
        }
    }

    FlightCommandParams params;
    params.target_altitude = altitude;
    params.duration_s = hover_duration;
    params.climb_rate = 0.4f;      // 0.4 m/s climb
    params.descent_rate = 0.3f;    // 0.3 m/s descent

    if (flight.executeCommand(FlightCommandType::JUMP, params)) {
        console.print("Jump command started (alt: %.2f m, hover: %.1f s)\r\n",
                     altitude, hover_duration);
        return 0;
    } else {
        console.print("Failed to start jump command\r\n");
        return 1;
    }
}

// Takeoff command: takeoff [altitude_m]
// 離陸コマンド: takeoff [高度_m]
static int cmd_takeoff(int argc, char** argv) {
    auto& console = Console::getInstance();
    auto& flight = FlightCommandService::getInstance();

    if (!flight.canExecute()) {
        console.print("Error: Cannot execute. Check landing/calibration status.\r\n");
        return 1;
    }

    if (flight.isRunning()) {
        console.print("Error: Another command is running. Use 'flight cancel' first.\r\n");
        return 1;
    }

    float altitude = 0.5f;  // Default 0.5m
    if (argc >= 2) {
        altitude = atof(argv[1]);
        if (altitude < 0.1f || altitude > 2.0f) {
            console.print("Error: Altitude must be 0.1-2.0 [m]\r\n");
            return 1;
        }
    }

    FlightCommandParams params;
    params.target_altitude = altitude;
    params.climb_rate = 0.3f;  // 0.3 m/s

    if (flight.executeCommand(FlightCommandType::TAKEOFF, params)) {
        console.print("Takeoff command started (target: %.2f m)\r\n", altitude);
        return 0;
    } else {
        console.print("Failed to start takeoff command\r\n");
        return 1;
    }
}

// Land command: land
// 着陸コマンド: land
static int cmd_land(int argc, char** argv) {
    auto& console = Console::getInstance();
    auto& flight = FlightCommandService::getInstance();

    if (flight.isRunning()) {
        console.print("Error: Another command is running. Use 'flight cancel' first.\r\n");
        return 1;
    }

    FlightCommandParams params;
    params.descent_rate = 0.3f;  // 0.3 m/s

    if (flight.executeCommand(FlightCommandType::LAND, params)) {
        console.print("Land command started\r\n");
        return 0;
    } else {
        console.print("Failed to start land command\r\n");
        return 1;
    }
}

// Hover command: hover [altitude_m] [duration_s]
// ホバリングコマンド: hover [高度_m] [時間_秒]
static int cmd_hover(int argc, char** argv) {
    auto& console = Console::getInstance();
    auto& flight = FlightCommandService::getInstance();

    if (flight.isRunning()) {
        console.print("Error: Another command is running. Use 'flight cancel' first.\r\n");
        return 1;
    }

    float altitude = 0.5f;  // Default 0.5m
    if (argc >= 2) {
        altitude = atof(argv[1]);
        if (altitude < 0.1f || altitude > 2.0f) {
            console.print("Error: Altitude must be 0.1-2.0 [m]\r\n");
            return 1;
        }
    }

    float duration = 5.0f;  // Default 5s
    if (argc >= 3) {
        duration = atof(argv[2]);
        if (duration < 0.1f || duration > 60.0f) {
            console.print("Error: Duration must be 0.1-60.0 [s]\r\n");
            return 1;
        }
    }

    FlightCommandParams params;
    params.target_altitude = altitude;
    params.duration_s = duration;

    if (flight.executeCommand(FlightCommandType::HOVER, params)) {
        console.print("Hover command started (alt: %.2f m, duration: %.1f s)\r\n",
                     altitude, duration);
        return 0;
    } else {
        console.print("Failed to start hover command\r\n");
        return 1;
    }
}

// Flight status/cancel: flight [status|cancel]
// 飛行状態/キャンセル: flight [status|cancel]
static int cmd_flight(int argc, char** argv) {
    auto& console = Console::getInstance();
    auto& flight = FlightCommandService::getInstance();

    if (argc < 2) {
        console.print("Usage: flight [status|cancel]\r\n");
        return 1;
    }

    if (strcmp(argv[1], "status") == 0) {
        // Show status
        // 状態表示
        if (flight.isRunning()) {
            const char* cmd_name = "UNKNOWN";
            switch (flight.getCurrentCommand()) {
                case FlightCommandType::JUMP:    cmd_name = "JUMP"; break;
                case FlightCommandType::TAKEOFF: cmd_name = "TAKEOFF"; break;
                case FlightCommandType::LAND:    cmd_name = "LAND"; break;
                case FlightCommandType::HOVER:   cmd_name = "HOVER"; break;
                default: break;
            }
            console.print("Flight command: %s\r\n", cmd_name);
            console.print("State: RUNNING\r\n");
            console.print("Elapsed: %.1f s\r\n", flight.getElapsedTime());
        } else {
            console.print("Flight command: NONE\r\n");
            console.print("State: IDLE\r\n");
        }
        return 0;

    } else if (strcmp(argv[1], "cancel") == 0) {
        // Cancel command
        // コマンドキャンセル
        if (flight.isRunning()) {
            flight.cancel();
            console.print("Flight command cancelled\r\n");
        } else {
            console.print("No command running\r\n");
        }
        return 0;

    } else {
        console.print("Unknown subcommand: %s\r\n", argv[1]);
        console.print("Usage: flight [status|cancel]\r\n");
        return 1;
    }
}

// Register flight commands
// 飛行コマンドを登録
void register_flight_commands() {
    const esp_console_cmd_t jump_cmd = {
        .command = "jump",
        .help = "Jump (takeoff, hover, land) [jump <altitude_m> <hover_sec>]",
        .hint = NULL,
        .func = &cmd_jump,
    };
    esp_console_cmd_register(&jump_cmd);

    const esp_console_cmd_t takeoff_cmd = {
        .command = "takeoff",
        .help = "Takeoff to specified altitude [takeoff <altitude_m>]",
        .hint = NULL,
        .func = &cmd_takeoff,
    };
    esp_console_cmd_register(&takeoff_cmd);

    const esp_console_cmd_t land_cmd = {
        .command = "land",
        .help = "Land the vehicle",
        .hint = NULL,
        .func = &cmd_land,
    };
    esp_console_cmd_register(&land_cmd);

    const esp_console_cmd_t hover_cmd = {
        .command = "hover",
        .help = "Hover at altitude [hover <altitude_m> <duration_s>]",
        .hint = NULL,
        .func = &cmd_hover,
    };
    esp_console_cmd_register(&hover_cmd);

    const esp_console_cmd_t flight_status_cmd = {
        .command = "flight",
        .help = "Flight command status [flight status|cancel]",
        .hint = NULL,
        .func = &cmd_flight,
    };
    esp_console_cmd_register(&flight_status_cmd);
}
