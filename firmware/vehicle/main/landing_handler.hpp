/**
 * @file landing_handler.hpp
 * @brief Landing detection and calibration handler
 *
 * Integrates landing detection, stationary detection, and level calibration.
 * Manages the calibration state machine and provides arm permission control.
 *
 * 着陸検出・キャリブレーション統合ハンドラ。
 * 着陸検出、静止検出、姿勢基準キャリブレーションを統合管理。
 * Arm許可制御を提供。
 */

#pragma once

#include "stationary_detector.hpp"
#include "level_calibrator.hpp"
#include "stampfly_math.hpp"
#include "system_state.hpp"
#include "esp_log.h"

namespace stampfly {

class LandingHandler {
public:
    /**
     * @brief Calibration state
     * @note Now uses CalibrationState from system_state.hpp (Single Source of Truth)
     * @note system_state.hppのCalibrationStateを使用（単一の真実の源）
     */
    // CalibrationState enum removed - use stampfly::CalibrationState from system_state.hpp

    struct Config {
        float landing_altitude_threshold;
        int landing_hold_samples;
        int tof_timeout_samples;

        Config()
            : landing_altitude_threshold(0.05f)  // [m] - altitude below this = landed
            , landing_hold_samples(80)           // 200ms @ 400Hz
            , tof_timeout_samples(800)           // 2s @ 400Hz - fallback if ToF unresponsive
        {}
    };

    /**
     * @brief Initialize handler
     */
    void init(const Config& config = Config()) {
        config_ = config;
        stationary_detector_.init();
        level_calibrator_.reset();
        reset();
        // Boot時は着陸・キャリブレーション済みで開始（main.cppのPhase 2-3が担当）
        // ARM時にreset()でNOT_STARTEDに戻り、着陸後に再キャリブレーションが動作する
        // Start as landed + calibrated after boot (main.cpp Phase 2-3 handles initial cal)
        // reset() on ARM reverts to NOT_STARTED, enabling post-flight recalibration
        is_landed_ = true;
        calibration_state_ = CalibrationState::COMPLETED;
        syncToSystemStateManager();
    }

    /**
     * @brief Reset to initial state (call on arm)
     */
    void reset() {
        calibration_state_ = CalibrationState::NOT_STARTED;
        is_landed_ = false;
        landing_count_ = 0;
        tof_high_count_ = 0;
        just_landed_ = false;
        just_calibrated_ = false;
        stationary_detector_.reset();

        // Sync to SystemStateManager
        // SystemStateManagerに同期
        syncToSystemStateManager();
    }

    /**
     * @brief Update handler state
     * @param is_disarmed True if vehicle is disarmed
     * @param tof_altitude ToF altitude reading [m]
     * @param gyro Gyroscope reading [rad/s]
     * @param accel Accelerometer reading [m/s²]
     */
    void update(bool is_disarmed, float tof_altitude,
                const math::Vector3& gyro, const math::Vector3& accel) {
        just_landed_ = false;
        just_calibrated_ = false;

        // If armed, reset state and wait for landing
        if (!is_disarmed) {
            if (calibration_state_ == CalibrationState::COMPLETED ||
                calibration_state_ == CalibrationState::CALIBRATING) {
                calibration_state_ = CalibrationState::WAITING_LANDING;
            }
            is_landed_ = false;
            landing_count_ = 0;
            stationary_detector_.reset();
            return;
        }

        // Disarmed - check for landing
        bool altitude_low = (tof_altitude < config_.landing_altitude_threshold);

        if (altitude_low) {
            // ToF detects ground nearby - normal landing path
            // ToFが近い地面を検出 - 通常の着陸パス
            landing_count_++;
            tof_high_count_ = 0;
            if (landing_count_ >= config_.landing_hold_samples && !is_landed_) {
                is_landed_ = true;
                just_landed_ = true;

                if (calibration_state_ != CalibrationState::COMPLETED) {
                    calibration_state_ = CalibrationState::CALIBRATING;
                    stationary_detector_.reset();
                }
            }
        } else {
            landing_count_ = 0;
            tof_high_count_++;

            // Fallback: if ToF consistently fails (low-reflectivity surface),
            // assume landed and start calibration using accel/gyro only.
            // フォールバック: ToFが継続的に失敗する場合（低反射面）、
            // 着陸と仮定してaccel/gyroのみでキャリブレーション開始
            if (tof_high_count_ >= config_.tof_timeout_samples && !is_landed_) {
                is_landed_ = true;
                just_landed_ = true;
                if (calibration_state_ != CalibrationState::COMPLETED) {
                    calibration_state_ = CalibrationState::CALIBRATING;
                    stationary_detector_.reset();
                    ESP_LOGW("LandingHandler",
                             "ToF timeout (%d samples) - assuming landed (low-reflectivity surface?)",
                             config_.tof_timeout_samples);
                }
            }

            if (is_landed_ && tof_high_count_ < config_.tof_timeout_samples) {
                // ToF suddenly reads high but hasn't timed out - might be picked up
                // ToFが突然高くなったがタイムアウトしていない - 持ち上げられた可能性
                is_landed_ = false;
                if (calibration_state_ == CalibrationState::COMPLETED) {
                    calibration_state_ = CalibrationState::NOT_STARTED;
                }
            }
        }

        // If landed and calibrating, run stationary detection
        if (is_landed_ && calibration_state_ == CalibrationState::CALIBRATING) {
            stationary_detector_.update(gyro, accel);

            if (stationary_detector_.isStationary()) {
                // Calibration complete
                gyro_bias_ = stationary_detector_.getGyroAverage();
                accel_reference_ = stationary_detector_.getAccelAverage();
                level_calibrator_.setReference(accel_reference_);

                calibration_state_ = CalibrationState::COMPLETED;
                just_calibrated_ = true;
            }
        }

        // Sync to SystemStateManager
        // SystemStateManagerに同期
        syncToSystemStateManager();
    }

    // === State queries ===

    /**
     * @brief Check if arm is allowed
     */
    bool canArm() const {
        return calibration_state_ == CalibrationState::COMPLETED;
    }

    /**
     * @brief Check if calibration is in progress
     */
    bool isCalibrating() const {
        return calibration_state_ == CalibrationState::CALIBRATING;
    }

    /**
     * @brief Check if vehicle is landed
     */
    bool isLanded() const { return is_landed_; }

    /**
     * @brief Get calibration state
     */
    CalibrationState getCalibrationState() const { return calibration_state_; }

    // === Event flags (single-shot, cleared each update) ===

    /**
     * @brief Check if just landed this frame
     */
    bool justLanded() const { return just_landed_; }

    /**
     * @brief Check if calibration just completed this frame
     */
    bool justCalibrated() const { return just_calibrated_; }

    // === Calibration results ===

    /**
     * @brief Get gyro bias from calibration
     */
    math::Vector3 getGyroBias() const { return gyro_bias_; }

    /**
     * @brief Get acceleration reference from calibration
     */
    math::Vector3 getAccelReference() const { return accel_reference_; }

    /**
     * @brief Get level calibrator (for attitude offset computation)
     */
    const LevelCalibrator& getLevelCalibrator() const { return level_calibrator_; }

private:
    /**
     * @brief Sync local state to SystemStateManager
     * @brief ローカル状態をSystemStateManagerに同期
     */
    void syncToSystemStateManager() {
        auto& sys_state_mgr = SystemStateManager::getInstance();

        // Update calibration state
        // キャリブレーション状態を更新
        sys_state_mgr.updateCalibrationState(calibration_state_);

        // Update readiness flags
        // 準備フラグを更新
        sys_state_mgr.setReady(ReadinessFlags::CALIBRATED,
                               calibration_state_ == CalibrationState::COMPLETED);
        sys_state_mgr.setReady(ReadinessFlags::LANDED, is_landed_);
    }

    Config config_;
    StationaryDetector stationary_detector_;
    LevelCalibrator level_calibrator_;

    CalibrationState calibration_state_ = CalibrationState::NOT_STARTED;
    bool is_landed_ = false;
    int landing_count_ = 0;
    int tof_high_count_ = 0;  // Counts consecutive ToF > threshold (for fallback)
                               // ToFが閾値超の連続カウント（フォールバック用）

    // Event flags
    bool just_landed_ = false;
    bool just_calibrated_ = false;

    // Calibration results
    math::Vector3 gyro_bias_;
    math::Vector3 accel_reference_;
};

}  // namespace stampfly
