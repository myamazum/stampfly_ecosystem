// High-Level Flight Command Service Implementation
// 高レベル飛行コマンドサービス実装
#include "flight_command.hpp"
#include "command_queue.hpp"
#include "system_state.hpp"
#include "control_arbiter.hpp"
#include "sensor_fusion.hpp"
#include "landing_handler.hpp"
#include "stampfly_state.hpp"
#include "esp_log.h"

// Forward declarations for globals
// グローバル変数の前方宣言
namespace globals {
    extern stampfly::LandingHandler g_landing_handler;
    extern sf::SensorFusion g_fusion;

    // ToF sensor buffer (for open-loop climb altitude check)
    // ToFセンサーバッファ（開ループ上昇の高度チェック用）
    constexpr int REF_BUFFER_SIZE = 100;
    extern float g_tof_bottom_buffer[REF_BUFFER_SIZE];
    extern int g_tof_bottom_buffer_index;
    extern int g_tof_bottom_buffer_count;
}

static const char* TAG = "FlightCmd";

namespace stampfly {

// Get singleton instance
// シングルトンインスタンスを取得
FlightCommandService& FlightCommandService::getInstance() {
    static FlightCommandService instance;
    return instance;
}

// Initialize the service
// サービスの初期化
esp_err_t FlightCommandService::init() {
    ESP_LOGI(TAG, "Initializing Flight Command Service");

    state_ = FlightCommandState::IDLE;
    current_command_ = FlightCommandType::NONE;
    phase_ = ExecutionPhase::INIT;
    elapsed_time_ = 0.0f;
    hover_timer_ = 0.0f;

    return ESP_OK;
}

// Execute command (non-blocking)
// コマンド実行（非ブロッキング）
bool FlightCommandService::executeCommand(FlightCommandType type, const FlightCommandParams& params) {
    // Enqueue command to CommandQueue
    // CommandQueueにコマンドを登録
    auto& queue = CommandQueue::getInstance();

    // Check if another command is running or queued
    // 他のコマンドが実行中またはキュー待ちかチェック
    if (isRunning() || !queue.isEmpty()) {
        ESP_LOGW(TAG, "Command queue not empty (running or queued commands exist)");
        // Still allow enqueueing - queue will handle priority
        // キューイング自体は許可 - キューが優先度を処理
    }

    // Auto-ARM for WiFi commands (enable debug mode)
    // WiFiコマンド用の自動ARM機能（デバッグモード有効化）
    auto& state_mgr = StampFlyState::getInstance();
    auto& sys_state_mgr = SystemStateManager::getInstance();

    // Enable debug mode to bypass some safety checks for WiFi commands
    // WiFiコマンド用に一部の安全チェックをバイパス
    state_mgr.setDebugMode(true);
    sys_state_mgr.setDebugMode(true);

    FlightState current_state = state_mgr.getFlightState();

    if (current_state != FlightState::ARMED && current_state != FlightState::FLYING) {
        // Need to ARM first
        // まずARMする必要がある

        // If not IDLE or ERROR, transition to IDLE first
        // IDLEまたはERROR状態でない場合、まずIDLEに遷移
        if (current_state != FlightState::IDLE && current_state != FlightState::ERROR) {
            ESP_LOGW(TAG, "Cannot ARM from state %d, transitioning to IDLE", static_cast<int>(current_state));
            state_mgr.setFlightState(FlightState::IDLE);
            sys_state_mgr.setFlightState(FlightState::IDLE);
        }

        // Request ARM
        // ARM要求
        if (!state_mgr.requestArm()) {
            ESP_LOGE(TAG, "Failed to ARM vehicle for WiFi command");
            state_mgr.setDebugMode(false);
            sys_state_mgr.setDebugMode(false);
            return false;
        }

        // Also ARM in SystemStateManager
        // SystemStateManagerでもARM
        sys_state_mgr.requestArm();

        ESP_LOGI(TAG, "Auto-ARMed for WiFi command");
    }

    // Enqueue to CommandQueue
    // CommandQueueに登録
    int cmd_id = queue.enqueue(type, params.target_altitude, params.duration_s);

    if (cmd_id < 0) {
        ESP_LOGE(TAG, "Failed to enqueue command (queue full)");
        state_mgr.setDebugMode(false);
        sys_state_mgr.setDebugMode(false);
        return false;
    }

    // Note: Do NOT set current_command_id_ here - it will be set in update()
    // when CommandQueue actually starts the command
    // 注意: ここではcurrent_command_id_を設定しない - CommandQueueが実際に
    // コマンドを開始したときにupdate()で設定される
    ESP_LOGI(TAG, "Command enqueued: ID=%d, type=%d", cmd_id, static_cast<int>(type));

    return true;
}

// Cancel current command
// 現在のコマンドをキャンセル
void FlightCommandService::cancel() {
    // Cancel current command in queue
    // キュー内の現在のコマンドをキャンセル
    auto& queue = CommandQueue::getInstance();

    if (current_command_id_ >= 0) {
        queue.cancel(current_command_id_);
        current_command_id_ = -1;
    }

    if (isRunning()) {
        ESP_LOGI(TAG, "Cancelling command: %d", static_cast<int>(current_command_));
        state_ = FlightCommandState::IDLE;
        current_command_ = FlightCommandType::NONE;
        phase_ = ExecutionPhase::INIT;

        // Send zero throttle to stop
        // ゼロスロットルで停止
        sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);
    }
}

// Update command execution (called from control task at 400Hz)
// 定期更新（制御タスクから400Hzで呼ばれる）
void FlightCommandService::update(float dt) {
    // Get current command from CommandQueue
    // CommandQueueから現在のコマンドを取得
    auto& queue = CommandQueue::getInstance();
    const CommandEntry* cmd = queue.getCurrentCommand();

    if (cmd == nullptr) {
        // No command running - reset state
        // コマンド実行中でない - 状態リセット
        if (isRunning()) {
            state_ = FlightCommandState::IDLE;
            current_command_ = FlightCommandType::NONE;
            phase_ = ExecutionPhase::INIT;
            elapsed_time_ = 0.0f;
            hover_timer_ = 0.0f;
            current_command_id_ = -1;
        }
        return;
    }

    // New command started - initialize
    // 新しいコマンド開始 - 初期化
    if (current_command_id_ != cmd->command_id) {
        ESP_LOGI(TAG, "Starting command from queue: ID=%d, type=%d",
                 cmd->command_id, static_cast<int>(cmd->type));
        current_command_id_ = cmd->command_id;
        current_command_ = cmd->type;
        params_.target_altitude = cmd->target_altitude;
        params_.duration_s = cmd->duration_s;
        params_.climb_rate = cmd->climb_rate;
        params_.descent_rate = cmd->descent_rate;
        state_ = FlightCommandState::RUNNING;
        phase_ = ExecutionPhase::INIT;
        elapsed_time_ = 0.0f;
        hover_timer_ = 0.0f;
    }

    elapsed_time_ += dt;

    // Get current altitude
    // 現在の高度を取得
    float current_altitude = getCurrentAltitude();

    // Debug log every 100 cycles (~250ms @ 400Hz)
    static int update_log_counter = 0;
    if (++update_log_counter >= 100) {
        ESP_LOGI(TAG, "FlightCommand::update() - cmd=%d, phase=%d, alt=%.3f m, elapsed=%.1f s",
                 static_cast<int>(current_command_), static_cast<int>(phase_),
                 current_altitude, elapsed_time_);
        update_log_counter = 0;
    }

    // Command-specific state machine
    // コマンド固有の状態マシン
    switch (current_command_) {
        case FlightCommandType::JUMP:
            updateJumpCommand(dt, current_altitude);
            break;

        case FlightCommandType::TAKEOFF:
            updateTakeoffCommand(dt, current_altitude);
            break;

        case FlightCommandType::LAND:
            updateLandCommand(dt, current_altitude);
            break;

        case FlightCommandType::HOVER:
            updateHoverCommand(dt, current_altitude);
            break;

        default:
            // Unknown command, fail
            // 未知のコマンド、失敗
            ESP_LOGW(TAG, "Unknown command type: %d", static_cast<int>(current_command_));
            state_ = FlightCommandState::FAILED;
            queue.markFailed();
            current_command_id_ = -1;
            break;
    }

    // Check if command completed or failed
    // コマンドが完了または失敗したかチェック
    if (state_ == FlightCommandState::COMPLETED || phase_ == ExecutionPhase::DONE) {
        ESP_LOGI(TAG, "Command completed: ID=%d", current_command_id_);
        queue.markCompleted();
        state_ = FlightCommandState::IDLE;
        current_command_ = FlightCommandType::NONE;
        phase_ = ExecutionPhase::INIT;
        current_command_id_ = -1;
    } else if (state_ == FlightCommandState::FAILED) {
        ESP_LOGW(TAG, "Command failed: ID=%d", current_command_id_);
        queue.markFailed();
        state_ = FlightCommandState::IDLE;
        current_command_ = FlightCommandType::NONE;
        phase_ = ExecutionPhase::INIT;
        current_command_id_ = -1;
        sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);  // Stop motors
    }

    // Safety timeout - fail if command takes too long
    // 安全タイムアウト - コマンドが長時間かかる場合は失敗
    const float MAX_COMMAND_TIME = 30.0f;  // 30 seconds
    if (elapsed_time_ > MAX_COMMAND_TIME) {
        ESP_LOGW(TAG, "Command timeout after %.1f seconds", elapsed_time_);
        state_ = FlightCommandState::FAILED;
        queue.markFailed();
        current_command_id_ = -1;
        sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);  // Stop motors
    }
}

// Check if command can be executed
// 実行可能かチェック
bool FlightCommandService::canExecute() const {
    // Check landing status
    // 着陸状態をチェック
    if (!globals::g_landing_handler.isLanded()) {
        ESP_LOGW(TAG, "Warning: vehicle not landed (allowing for WiFi commands)");
        // Don't block - allow WiFi commands even when not landed
        // WiFiコマンドのために許可（着陸検出なしでも実行可能）
    }

    // Check calibration status
    // キャリブレーション状態をチェック
    if (!globals::g_landing_handler.canArm()) {
        ESP_LOGW(TAG, "Calibration not completed - command rejected");
        // Block execution - calibration is required for safe flight
        // キャリブレーション必須（安全な飛行のため）
        return false;
    }

    // TODO: Add battery voltage check
    // バッテリー電圧チェックを追加

    // For WiFi commands, always allow execution (user responsibility)
    // WiFiコマンドは常に実行許可（ユーザーの責任）
    return true;
}

// Send control input to ControlArbiter
// 制御出力を ControlArbiter に送る
void FlightCommandService::sendControlInput(float throttle, float roll, float pitch, float yaw) {
    // Send to ControlArbiter via WebSocket source
    // WebSocketソース経由でControlArbiterに送信
    auto& arbiter = ControlArbiter::getInstance();
    arbiter.updateFromWebSocket(throttle, roll, pitch, yaw, 0);

    // Debug log every 100 cycles (~250ms @ 400Hz)
    static int send_log_counter = 0;
    if (++send_log_counter >= 100) {
        ESP_LOGI(TAG, "→ ControlArbiter: T=%.2f R=%.2f P=%.2f Y=%.2f", throttle, roll, pitch, yaw);
        send_log_counter = 0;
    }
}

// Get current altitude estimate
// 現在の高度推定値を取得
float FlightCommandService::getCurrentAltitude() const {
    // Get altitude from sensor fusion (NED frame, so negative = up)
    // センサーフュージョンから高度を取得（NEDフレームなので負の値が上方向）
    auto state = globals::g_fusion.getState();

    // Return positive altitude (negate Z in NED frame)
    // 正の高度を返す（NEDフレームのZを反転）
    return -state.position.z;
}

// ============================================================================
// Command-specific update functions
// コマンド固有の更新関数
// ============================================================================

void FlightCommandService::updateJumpCommand(float dt, float current_altitude) {
    // JUMP command state machine: INIT → OPEN_LOOP_CLIMB → CLIMBING → DESCENDING → DONE
    // JUMPコマンド状態マシン: INIT → 開ループ上昇 → フィードバック上昇 → 降下 → 完了

    switch (phase_) {
        case ExecutionPhase::INIT:
            // Start open-loop climb to enable flow sensor
            // 開ループ上昇開始（フローセンサー有効化のため）
            ESP_LOGI(TAG, "JUMP: Starting open-loop climb to 0.10m (target: %.2f m)",
                     params_.target_altitude);
            phase_ = ExecutionPhase::OPEN_LOOP_CLIMB;
            break;

        case ExecutionPhase::OPEN_LOOP_CLIMB:
            // Open-loop climb to ~10cm to enable optical flow sensor
            // フローセンサー有効化のため~10cmまで開ループ上昇
            {
                constexpr float TAKEOFF_HEIGHT = 0.10f;  // Height to enable flow sensor / フローセンサー有効高度
                constexpr float OPEN_LOOP_THROTTLE = 0.75f;  // Fixed throttle for initial climb / 初期上昇の固定スロットル

                // Use raw ToF altitude during open-loop climb (ESKF position estimation not yet active)
                // 開ループ上昇中はToF生値を使用（ESKF位置推定はまだ非アクティブ）
                float tof_altitude = 0.0f;
                if (globals::g_tof_bottom_buffer_count > 0) {
                    int tof_latest_idx = (globals::g_tof_bottom_buffer_index - 1 + globals::REF_BUFFER_SIZE) % globals::REF_BUFFER_SIZE;
                    tof_altitude = globals::g_tof_bottom_buffer[tof_latest_idx];
                }

                if (tof_altitude >= TAKEOFF_HEIGHT) {
                    // Reached takeoff height, switch to closed-loop control
                    // 離陸高度到達、フィードバック制御に切り替え
                    ESP_LOGI(TAG, "JUMP: Reached takeoff height %.2f m (ToF), switching to closed-loop control",
                             tof_altitude);
                    phase_ = ExecutionPhase::CLIMBING;
                } else {
                    // Continue open-loop climb
                    // 開ループ上昇継続
                    sendControlInput(OPEN_LOOP_THROTTLE, 0.0f, 0.0f, 0.0f);
                }
            }
            break;

        case ExecutionPhase::CLIMBING:
            // Climb until target altitude reached
            // 目標高度に到達するまで上昇
            {
                float altitude_error = params_.target_altitude - current_altitude;

                if (altitude_error < 0.05f) {  // Within 5cm of target
                    // Reached target, start descending (skip hovering to prevent overshoot)
                    // 目標到達、降下開始（オーバーシュート防止のためホバリングスキップ）
                    ESP_LOGI(TAG, "JUMP: Reached %.2f m, starting descent",
                             current_altitude);
                    phase_ = ExecutionPhase::DESCENDING;
                } else {
                    // Continue climbing with throttle based on climb rate
                    // 上昇速度に基づいたスロットルで上昇継続
                    // Simple proportional control: higher throttle for larger error
                    // シンプルな比例制御：誤差が大きいほど高いスロットル
                    float throttle = 0.75f + (altitude_error * 0.6f);
                    throttle = constrain(throttle, 0.70f, 0.95f);  // Limit range

                    // Debug log every 100 cycles (~250ms @ 400Hz)
                    static int log_counter = 0;
                    if (++log_counter >= 100) {
                        ESP_LOGI(TAG, "JUMP CLIMBING: alt=%.3f m, target=%.2f m, error=%.3f m, throttle=%.2f",
                                 current_altitude, params_.target_altitude, altitude_error, throttle);
                        log_counter = 0;
                    }

                    sendControlInput(throttle, 0.0f, 0.0f, 0.0f);
                }
            }
            break;

        case ExecutionPhase::HOVERING:
            // Hover at target altitude for specified duration
            // 指定時間、目標高度でホバリング
            hover_timer_ += dt;

            if (hover_timer_ >= params_.duration_s) {
                // Hover complete, start descending
                // ホバリング完了、降下開始
                ESP_LOGI(TAG, "JUMP: Hover complete, descending");
                phase_ = ExecutionPhase::DESCENDING;
            } else {
                // Maintain altitude with proportional control
                // 比例制御で高度維持
                float altitude_error = params_.target_altitude - current_altitude;
                float throttle = 0.55f + (altitude_error * 0.6f);
                throttle = constrain(throttle, 0.50f, 0.75f);

                sendControlInput(throttle, 0.0f, 0.0f, 0.0f);
            }
            break;

        case ExecutionPhase::DESCENDING:
            // Descend until landed
            // 着陸するまで降下
            if (current_altitude < 0.05f) {  // Below 5cm = landed
                // Landed, command complete
                // 着陸、コマンド完了
                ESP_LOGI(TAG, "JUMP: Landed, command complete");
                phase_ = ExecutionPhase::DONE;
                sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);  // Stop motors
            } else {
                // Rapid descent with zero throttle (free fall)
                // ゼロスロットルで急降下（自由落下）
                sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);
            }
            break;

        case ExecutionPhase::DONE:
            // Command complete, reset to IDLE
            // コマンド完了、IDLE状態にリセット
            ESP_LOGI(TAG, "JUMP: Command complete, returning to IDLE");
            state_ = FlightCommandState::IDLE;
            current_command_ = FlightCommandType::NONE;
            phase_ = ExecutionPhase::INIT;
            break;
    }
}

void FlightCommandService::updateTakeoffCommand(float dt, float current_altitude) {
    // TAKEOFF: INIT → CLIMBING → DONE
    switch (phase_) {
        case ExecutionPhase::INIT:
            ESP_LOGI(TAG, "TAKEOFF: Starting climb to %.2f m", params_.target_altitude);
            phase_ = ExecutionPhase::CLIMBING;
            break;

        case ExecutionPhase::CLIMBING:
            {
                float altitude_error = params_.target_altitude - current_altitude;
                if (altitude_error < 0.05f) {
                    ESP_LOGI(TAG, "TAKEOFF: Reached %.2f m", current_altitude);
                    phase_ = ExecutionPhase::DONE;
                } else {
                    float throttle = 0.75f + (altitude_error * 0.6f);
                    throttle = constrain(throttle, 0.70f, 0.95f);
                    sendControlInput(throttle, 0.0f, 0.0f, 0.0f);
                }
            }
            break;

        case ExecutionPhase::DONE:
            state_ = FlightCommandState::COMPLETED;
            current_command_ = FlightCommandType::NONE;
            // Keep motors running at hover throttle
            // ホバースロットルでモーター継続
            sendControlInput(0.55f, 0.0f, 0.0f, 0.0f);
            break;

        default:
            break;
    }
}

void FlightCommandService::updateLandCommand(float dt, float current_altitude) {
    // LAND: INIT → DESCENDING → DONE
    switch (phase_) {
        case ExecutionPhase::INIT:
            ESP_LOGI(TAG, "LAND: Starting descent");
            phase_ = ExecutionPhase::DESCENDING;
            break;

        case ExecutionPhase::DESCENDING:
            if (current_altitude < 0.05f) {
                ESP_LOGI(TAG, "LAND: Landed");
                phase_ = ExecutionPhase::DONE;
                sendControlInput(0.0f, 0.0f, 0.0f, 0.0f);
            } else {
                // Gentle descent with proportional throttle
                // 穏やかなスロットルで降下継続
                float throttle = 0.35f + (current_altitude * 0.05f);
                throttle = constrain(throttle, 0.25f, 0.45f);
                sendControlInput(throttle, 0.0f, 0.0f, 0.0f);
            }
            break;

        case ExecutionPhase::DONE:
            // Command complete, reset to IDLE
            // コマンド完了、IDLE状態にリセット
            ESP_LOGI(TAG, "LAND: Command complete, returning to IDLE");
            state_ = FlightCommandState::IDLE;
            current_command_ = FlightCommandType::NONE;
            phase_ = ExecutionPhase::INIT;
            break;

        default:
            break;
    }
}

void FlightCommandService::updateHoverCommand(float dt, float current_altitude) {
    // HOVER: INIT → HOVERING → DONE
    switch (phase_) {
        case ExecutionPhase::INIT:
            ESP_LOGI(TAG, "HOVER: Hovering at %.2f m for %.1f s",
                     params_.target_altitude, params_.duration_s);
            phase_ = ExecutionPhase::HOVERING;
            hover_timer_ = 0.0f;
            break;

        case ExecutionPhase::HOVERING:
            hover_timer_ += dt;
            if (hover_timer_ >= params_.duration_s) {
                ESP_LOGI(TAG, "HOVER: Duration complete");
                phase_ = ExecutionPhase::DONE;
            } else {
                float altitude_error = params_.target_altitude - current_altitude;
                float throttle = 0.55f + (altitude_error * 0.6f);
                throttle = constrain(throttle, 0.50f, 0.75f);
                sendControlInput(throttle, 0.0f, 0.0f, 0.0f);
            }
            break;

        case ExecutionPhase::DONE:
            state_ = FlightCommandState::COMPLETED;
            current_command_ = FlightCommandType::NONE;
            sendControlInput(0.55f, 0.0f, 0.0f, 0.0f);  // Keep hovering
            break;

        default:
            break;
    }
}

// Constrain helper function
// 制約ヘルパー関数
float FlightCommandService::constrain(float value, float min, float max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
}

} // namespace stampfly
