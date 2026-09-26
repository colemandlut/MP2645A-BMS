/* 主机端单元测试: gcc -std=c11 -Wall -Wextra -I../src ../src/bms_logic.c test_bms_logic.c */
#include <stdio.h>
#include <stdlib.h>

#include "bms_logic.h"

static int fails, checks;
#define CHECK(c) do { checks++; if (!(c)) { fails++; printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); } } while (0)

static bms_meas_t nominal(void)
{
    bms_meas_t m = {0};
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3300;
    for (int i = 0; i < BMS_NTC_CH; i++) m.temp_dc[i] = 250;
    m.load_present = true;
    return m;
}

static bms_out_t run(bms_state_t *s, const bms_meas_t *m, uint32_t ms)
{
    bms_out_t o = {0};
    for (uint32_t t = 0; t < ms; t += BMS_TICK_MS) o = bms_step(s, m);
    return o;
}

static void test_nominal_all_on(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    bms_out_t o = run(&s, &m, 5000);
    CHECK(o.chg_fet && o.dsg_fet && o.faults == 0 && !o.bal_clk && o.passive_mask == 0);
}

static void test_cell_ov_debounce_and_recover(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.cell_mv[3] = 3660;
    bms_out_t o = run(&s, &m, CELL_OV_DELAY_MS - BMS_TICK_MS);
    CHECK(o.chg_fet);                          /* 去抖期内不动作 */
    o = run(&s, &m, BMS_TICK_MS);
    CHECK(!o.chg_fet && o.dsg_fet && (o.faults & FLT_CELL_OV));
    m.cell_mv[3] = 3450;                       /* 高于恢复点, 仍保持 */
    o = run(&s, &m, 5000);
    CHECK(!o.chg_fet);
    m.cell_mv[3] = 3390;
    o = run(&s, &m, CELL_OV_DELAY_MS);
    CHECK(o.chg_fet && o.faults == 0);
}

static void test_ov_discharge_avoids_body_diode(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.cell_mv[0] = 3660;
    run(&s, &m, 2000);
    m.current_a = -150;
    bms_out_t o = bms_step(&s, &m);
    CHECK(o.chg_fet && o.dsg_fet);
}

static void test_cell_uv(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.cell_mv[7] = 2450;
    bms_out_t o = run(&s, &m, 2000);
    CHECK(!o.dsg_fet && o.chg_fet && (o.faults & FLT_CELL_UV));
    m.current_a = 50;                          /* 充电中: 打开 DSG, 避免走体二极管 */
    o = bms_step(&s, &m);
    CHECK(o.dsg_fet);
}

static void test_ocd1_200a_ok_220a_trips(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.current_a = -200;
    bms_out_t o = run(&s, &m, 60000);
    CHECK(o.dsg_fet && o.faults == 0);         /* 200A 持续允许 */
    m.current_a = -225;
    o = run(&s, &m, OCD1_DELAY_MS);
    CHECK(!o.dsg_fet && (o.faults & FLT_OCD1));
    m.current_a = 0;
    o = run(&s, &m, OC_RECOVER_MS);
    CHECK(o.dsg_fet && o.faults == 0);         /* 自动重试 */
}

static void test_ocd2_fast(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.current_a = -320;
    bms_out_t o = run(&s, &m, OCD2_DELAY_MS);
    CHECK(!o.dsg_fet && (o.faults & FLT_OCD2));
}

static void test_occ(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.current_a = 120;                         /* 1C 充电：允许 */
    bms_out_t o = run(&s, &m, 60000);
    CHECK(o.chg_fet && o.faults == 0);
    m.current_a = 135;                         /* > 1.1C：跳闸 */
    o = run(&s, &m, OCC_DELAY_MS);
    CHECK(!o.chg_fet && o.dsg_fet && (o.faults & FLT_OCC));
}

static void test_hw_scp_latch_until_load_removed(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.hw_scp = true;
    bms_out_t o = bms_step(&s, &m);
    CHECK(!o.chg_fet && !o.dsg_fet);
    m.hw_scp = false;
    o = run(&s, &m, 60000);
    CHECK(!o.dsg_fet);                         /* 负载仍在, 保持锁存 */
    m.load_present = false;
    o = run(&s, &m, 1000);
    CHECK(o.dsg_fet && o.chg_fet);
}

static void test_charge_below_zero_blocked(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.temp_dc[1] = -50;
    bms_out_t o = run(&s, &m, TEMP_DELAY_MS);
    CHECK(!o.chg_fet && o.dsg_fet && (o.faults & FLT_CHG_UT));
}

static void test_fet_ot_blocks_both(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.temp_dc[2] = 1050;
    bms_out_t o = run(&s, &m, TEMP_DELAY_MS);
    CHECK(!o.chg_fet && !o.dsg_fet);
}

static void test_no_balance_on_plateau(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.cell_mv[2] = 3340;                       /* 平台区 40mV 差, 充电中 */
    m.current_a = 50;
    bms_out_t o = run(&s, &m, 10000);
    CHECK(!o.bal_clk && o.passive_mask == 0);
}

static void test_top_balance_start_stop(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3420;
    m.cell_mv[5] = 3460;
    m.current_a = 50;
    bms_out_t o = bms_step(&s, &m);
    CHECK(o.bal_clk && o.passive_mask == 0);
    m.cell_mv[5] = 3435;                       /* 15mV: 仍在迟滞内 */
    o = bms_step(&s, &m);
    CHECK(o.bal_clk);
    m.cell_mv[5] = 3428;                       /* 8mV: 停止主动, 转被动微调 */
    o = bms_step(&s, &m);
    CHECK(!o.bal_clk && o.passive_mask == (1u << 5));
}

static void test_no_balance_when_diff_abnormal(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3450;
    m.cell_mv[3] = 3100;                       /* 350mV：坏电芯或采样断线 */
    bms_out_t o = bms_step(&s, &m);
    CHECK(!o.bal_clk);
}

static void test_no_balance_when_cell_low(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3100;
    m.cell_mv[0] = 2950;                       /* 低于 3.0V：栅压不足 */
    bms_out_t o = run(&s, &m, BAL_REST_TIME_MS);
    CHECK(!o.bal_clk);
}

/* 开关电容简化模型：每步相邻两节按压差的一部分交换电荷（高→低），验证策略能收敛并停下 */
static void test_converges(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    static const int16_t pat[BMS_CELLS] = {3400, 3480, 3410, 3470, 3405, 3490, 3415, 3460};
    int32_t mv10[BMS_CELLS];
    for (int i = 0; i < BMS_CELLS; i++) { m.cell_mv[i] = pat[i]; mv10[i] = pat[i] * 10; }
    int steps = 0;
    bms_out_t o = bms_step(&s, &m);
    CHECK(o.bal_clk);
    while (o.bal_clk && steps < 20000) {
        int32_t d[BMS_CELLS - 1];
        for (int k = 0; k < BMS_CELLS - 1; k++) d[k] = (mv10[k + 1] - mv10[k]) / 8;
        for (int k = 0; k < BMS_CELLS - 1; k++) { mv10[k] += d[k]; mv10[k + 1] -= d[k]; }
        for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = (uint16_t)(mv10[i] / 10);
        o = bms_step(&s, &m);
        steps++;
    }
    CHECK(!o.bal_clk);
    CHECK(bms_cell_max(&m) - bms_cell_min(&m) <= BAL_DIFF_STOP_MV);
    printf("  收敛: %d 步, 最终压差 %d mV\n", steps, bms_cell_max(&m) - bms_cell_min(&m));
}

static void test_rest_balance(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    m.cell_mv[4] = 3390;                       /* 平台区 90mV 差 */
    bms_out_t o = run(&s, &m, BAL_REST_TIME_MS - BMS_TICK_MS);
    CHECK(!o.bal_clk);
    o = run(&s, &m, BMS_TICK_MS);
    CHECK(o.bal_clk);
    m.current_a = -100;                        /* 开始放电, 退出静置均衡 */
    o = bms_step(&s, &m);
    CHECK(!o.bal_clk);
}

static void test_balance_blocked_when_cold(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3450;
    m.cell_mv[0] = 3500;
    m.temp_dc[0] = -10;
    bms_out_t o = bms_step(&s, &m);
    CHECK(!o.bal_clk && o.passive_mask == 0);
}

static void test_balance_stops_on_fault(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3450;
    m.cell_mv[3] = 3500;
    bms_out_t o = bms_step(&s, &m);
    CHECK(o.bal_clk);
    m.temp_dc[2] = 1050;                       /* MOSFET 过温故障 */
    o = run(&s, &m, TEMP_DELAY_MS);
    CHECK(!o.bal_clk);
}

static void test_passive_mask_no_adjacent(void)
{
    bms_state_t s; bms_init(&s);
    bms_meas_t m = nominal();
    for (int i = 0; i < BMS_CELLS; i++) m.cell_mv[i] = 3420;
    m.cell_mv[0] = 3380;                       /* 最低, 其余全部高 40mV → 触发主动 */
    bms_out_t o = bms_step(&s, &m);
    CHECK(o.bal_clk);
    m.cell_mv[0] = 3412;                       /* 8mV: 被动, 相邻不同时开 */
    o = bms_step(&s, &m);
    CHECK(!o.bal_clk);
    CHECK((o.passive_mask & (o.passive_mask << 1)) == 0);
    CHECK(o.passive_mask != 0 && !(o.passive_mask & 1u));
}

int main(void)
{
    test_nominal_all_on();
    test_cell_ov_debounce_and_recover();
    test_ov_discharge_avoids_body_diode();
    test_cell_uv();
    test_ocd1_200a_ok_220a_trips();
    test_ocd2_fast();
    test_occ();
    test_hw_scp_latch_until_load_removed();
    test_charge_below_zero_blocked();
    test_fet_ot_blocks_both();
    test_no_balance_on_plateau();
    test_top_balance_start_stop();
    test_no_balance_when_diff_abnormal();
    test_no_balance_when_cell_low();
    test_converges();
    test_rest_balance();
    test_balance_blocked_when_cold();
    test_balance_stops_on_fault();
    test_passive_mask_no_adjacent();
    printf("%d/%d checks passed\n", checks - fails, checks);
    return fails ? EXIT_FAILURE : EXIT_SUCCESS;
}
