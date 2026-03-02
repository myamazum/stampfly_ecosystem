/**
 * @file workshop_globals.hpp
 * @brief Global variable declarations for workshop firmware
 *        ワークショップファームウェア用グローバル変数宣言
 *
 * Uses the same `globals` namespace and variable names as the vehicle firmware,
 * so that vehicle sensor tasks (IMU, Baro, LED, etc.) can be compiled and linked
 * without modification.
 *
 * Students should NOT include this file - use workshop_api.hpp instead.
 */

#pragma once

// Include the vehicle's globals.hpp to get all extern declarations
// vehicle の globals.hpp をインクルードして全てのextern宣言を取得
// The vehicle tasks reference these via relative include "../globals.hpp"
// which resolves to vehicle/main/globals.hpp. The workshop provides
// definitions for these same symbols in workshop_globals.cpp.
#include "globals.hpp"

// =============================================================================
// Workshop-specific additions (not in vehicle globals)
// ワークショップ固有の追加（vehicleのglobalsにない）
// =============================================================================

// Boot sequence flags
// 起動シーケンスフラグ
namespace globals {
extern volatile bool g_boot_complete;   // Set by app_main after init
extern volatile bool g_setup_complete;  // Set by ControlTask after setup()
} // namespace globals

