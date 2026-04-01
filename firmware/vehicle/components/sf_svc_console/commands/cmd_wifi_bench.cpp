/**
 * @file cmd_wifi_bench.cpp
 * @brief WiFi benchmark command - measures UDP/TCP send latency
 *
 * WiFiベンチマークコマンド - UDP/TCP送信レイテンシを計測
 *
 * Usage:
 *   wifi_bench [dest_ip]      - Run benchmark (default dest: 192.168.4.2)
 *   wifi_bench 192.168.4.100  - Specify destination IP for UDP
 *
 * Measures:
 *   1. UDP sendto() latency for various packet sizes
 *   2. TCP httpd_ws_send_frame_async() latency (if WebSocket client connected)
 *   3. Continuous send test with ESP-NOW coexistence check
 */

#include "console.hpp"
#include "telemetry.hpp"
#include "esp_console.h"
#include "esp_timer.h"
#include "esp_log.h"

#include <lwip/sockets.h>
#include <lwip/netdb.h>
#include <arpa/inet.h>

#include <cstring>
#include <cstdlib>
#include <algorithm>

static const char* TAG = "WiFiBench";

using namespace stampfly;

// =============================================================================
// Statistics helper
// 統計ヘルパー
// =============================================================================

struct BenchStats {
    uint64_t times[200];
    int count = 0;

    void record(uint64_t us) {
        if (count < 200) {
            times[count++] = us;
        }
    }

    void compute(uint64_t& avg, uint64_t& min_v, uint64_t& max_v, uint64_t& p99) const {
        if (count == 0) {
            avg = min_v = max_v = p99 = 0;
            return;
        }

        // Copy and sort for percentile
        // ソートしてパーセンタイル計算
        uint64_t sorted[200];
        memcpy(sorted, times, count * sizeof(uint64_t));
        std::sort(sorted, sorted + count);

        min_v = sorted[0];
        max_v = sorted[count - 1];
        p99 = sorted[(int)(count * 0.99)];

        uint64_t sum = 0;
        for (int i = 0; i < count; i++) sum += sorted[i];
        avg = sum / count;
    }
};

// =============================================================================
// UDP benchmark
// UDPベンチマーク
// =============================================================================

static void bench_udp(Console& console, const char* dest_ip, int iterations)
{
    // Create temporary UDP socket
    // 一時的なUDPソケット作成
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        console.print("ERROR: socket() failed: %d\r\n", errno);
        return;
    }

    struct sockaddr_in dest_addr = {};
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(8890);
    inet_aton(dest_ip, &dest_addr.sin_addr);

    // Test buffer (filled with dummy data)
    // テストバッファ（ダミーデータ）
    uint8_t buf[1024];
    memset(buf, 0xAA, sizeof(buf));

    int sizes[] = {117, 325, 840};
    int num_sizes = 3;

    console.print("\r\nUDP sendto() → %s:8890\r\n", dest_ip);
    console.print("  Size   avg      min      max      P99      [us]\r\n");
    console.print("  ─────────────────────────────────────────────────\r\n");

    for (int s = 0; s < num_sizes; s++) {
        int size = sizes[s];
        BenchStats stats;

        for (int i = 0; i < iterations; i++) {
            uint64_t start = esp_timer_get_time();
            sendto(sock, buf, size, 0,
                   (struct sockaddr*)&dest_addr, sizeof(dest_addr));
            uint64_t elapsed = esp_timer_get_time() - start;
            stats.record(elapsed);

            // Small delay to avoid flooding
            // フラッディング防止の小さな遅延
            vTaskDelay(pdMS_TO_TICKS(1));
        }

        uint64_t avg, min_v, max_v, p99;
        stats.compute(avg, min_v, max_v, p99);
        console.print("  %3dB:  %-8llu %-8llu %-8llu %-8llu\r\n",
                       size, avg, min_v, max_v, p99);
    }

    close(sock);
}

// =============================================================================
// UDP continuous send test (ESP-NOW coexistence)
// UDP連続送信テスト（ESP-NOW共存確認）
// =============================================================================

static void bench_udp_continuous(Console& console, const char* dest_ip,
                                  int size, int rate_hz, int duration_sec)
{
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        console.print("ERROR: socket() failed: %d\r\n", errno);
        return;
    }

    struct sockaddr_in dest_addr = {};
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(8890);
    inet_aton(dest_ip, &dest_addr.sin_addr);

    uint8_t buf[1024];
    memset(buf, 0xBB, sizeof(buf));

    int total_sends = rate_hz * duration_sec;
    int interval_ms = 1000 / rate_hz;
    BenchStats stats;

    console.print("\r\nUDP continuous: %dB × %dHz × %ds = %d packets\r\n",
                   size, rate_hz, duration_sec, total_sends);

    TickType_t next_wake = xTaskGetTickCount();

    for (int i = 0; i < total_sends && i < 200; i++) {
        uint64_t start = esp_timer_get_time();
        sendto(sock, buf, size, 0,
               (struct sockaddr*)&dest_addr, sizeof(dest_addr));
        uint64_t elapsed = esp_timer_get_time() - start;
        stats.record(elapsed);

        next_wake += pdMS_TO_TICKS(interval_ms);
        vTaskDelayUntil(&next_wake, pdMS_TO_TICKS(interval_ms));
    }

    uint64_t avg, min_v, max_v, p99;
    stats.compute(avg, min_v, max_v, p99);
    console.print("  avg=%-6lluus  min=%-6lluus  max=%-6lluus  P99=%-6lluus\r\n",
                   avg, min_v, max_v, p99);

    close(sock);
}

// =============================================================================
// TCP (WebSocket) benchmark
// TCP（WebSocket）ベンチマーク
// =============================================================================

static void bench_tcp(Console& console, int iterations)
{
    auto& telemetry = Telemetry::getInstance();

    if (!telemetry.hasClients()) {
        console.print("\r\nTCP ws_send_async(): SKIP (no WebSocket client connected)\r\n");
        console.print("  → Connect browser to http://192.168.4.1 and retry\r\n");
        return;
    }

    uint8_t buf[840];
    memset(buf, 0xCC, sizeof(buf));

    console.print("\r\nTCP httpd_ws_send_frame_async() [WebSocket client]\r\n");
    console.print("  Size   avg      min      max      P99      [us]\r\n");
    console.print("  ─────────────────────────────────────────────────\r\n");

    BenchStats stats;

    for (int i = 0; i < iterations; i++) {
        uint64_t start = esp_timer_get_time();
        telemetry.broadcast(buf, 840);
        uint64_t elapsed = esp_timer_get_time() - start;
        stats.record(elapsed);

        // Match telemetry send rate (~10ms)
        // テレメトリ送信レートに合わせる
        vTaskDelay(pdMS_TO_TICKS(10));
    }

    uint64_t avg, min_v, max_v, p99;
    stats.compute(avg, min_v, max_v, p99);
    console.print("  840B:  %-8llu %-8llu %-8llu %-8llu\r\n",
                   avg, min_v, max_v, p99);
}

// =============================================================================
// Main command handler
// メインコマンドハンドラ
// =============================================================================

static int cmd_wifi_bench(int argc, char** argv)
{
    auto& console = Console::getInstance();

    // Default destination: first DHCP client (192.168.4.2)
    // デフォルト送信先: 最初のDHCPクライアント
    const char* dest_ip = "192.168.4.2";
    if (argc >= 2) {
        dest_ip = argv[1];
    }

    int iterations = 100;

    console.print("=== WiFi Benchmark (%d iterations) ===\r\n", iterations);

    // 1. UDP latency test
    // UDP レイテンシテスト
    bench_udp(console, dest_ip, iterations);

    // 2. TCP (WebSocket) latency test
    // TCP（WebSocket）レイテンシテスト
    bench_tcp(console, iterations);

    // 3. UDP continuous send test (simulating telemetry)
    // UDP 連続送信テスト（テレメトリシミュレーション）
    bench_udp_continuous(console, dest_ip, 325, 100, 2);

    console.print("\r\n=== Benchmark complete ===\r\n");
    return 0;
}

// =============================================================================
// Command registration
// コマンド登録
// =============================================================================

extern "C" void register_wifi_bench_command()
{
    const esp_console_cmd_t cmd = {
        .command = "wifi_bench",
        .help = "WiFi UDP/TCP send latency benchmark\r\n"
                "  Usage: wifi_bench [dest_ip]\r\n"
                "  Default dest: 192.168.4.2",
        .hint = NULL,
        .func = &cmd_wifi_bench,
        .argtable = NULL,
    };
    esp_console_cmd_register(&cmd);
}
