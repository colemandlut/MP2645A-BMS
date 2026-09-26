#include "bms_logic.h"

#include <string.h>

enum {
    I_OV, I_UV, I_OCD1, I_OCD2, I_OCC, I_CHG_OT, I_CHG_UT,
    I_DSG_OT, I_DSG_UT, I_FET_OT, I_HW_SCP,
};

void bms_init(bms_state_t *s)
{
    memset(s, 0, sizeof(*s));
}

uint16_t bms_cell_max(const bms_meas_t *m)
{
    uint16_t v = 0;
    for (int i = 0; i < BMS_CELLS; i++)
        if (m->cell_mv[i] > v) v = m->cell_mv[i];
    return v;
}

uint16_t bms_cell_min(const bms_meas_t *m)
{
    uint16_t v = UINT16_MAX;
    for (int i = 0; i < BMS_CELLS; i++)
        if (m->cell_mv[i] < v) v = m->cell_mv[i];
    return v;
}

/* 带去抖的故障置位 / 清除: 条件连续满足 delay_ms 后才动作 */
static void eval(bms_state_t *s, uint32_t bit, int idx, bool trip, bool clear,
                 uint32_t trip_ms, uint32_t clear_ms)
{
    bool active = s->faults & bit;
    bool cond = active ? clear : trip;
    if (!cond) {
        s->tmr[idx] = 0;
        return;
    }
    s->tmr[idx] += BMS_TICK_MS;
    if (s->tmr[idx] >= (active ? clear_ms : trip_ms)) {
        s->faults ^= bit;
        s->tmr[idx] = 0;
    }
}

static void protect(bms_state_t *s, const bms_meas_t *m)
{
    uint16_t vmax = bms_cell_max(m), vmin = bms_cell_min(m);
    int16_t i = m->current_a;
    int16_t tc_hi = m->temp_dc[0] > m->temp_dc[1] ? m->temp_dc[0] : m->temp_dc[1];
    int16_t tc_lo = m->temp_dc[0] < m->temp_dc[1] ? m->temp_dc[0] : m->temp_dc[1];
    int16_t tfet = m->temp_dc[2];

    eval(s, FLT_CELL_OV, I_OV, vmax >= CELL_OV_TRIP_MV, vmax <= CELL_OV_RECOVER_MV,
         CELL_OV_DELAY_MS, CELL_OV_DELAY_MS);
    eval(s, FLT_CELL_UV, I_UV, vmin <= CELL_UV_TRIP_MV, vmin >= CELL_UV_RECOVER_MV,
         CELL_UV_DELAY_MS, CELL_UV_DELAY_MS);

    /* 过流: MOSFET 关断后电流为 0, 只能按时间自动重试 */
    eval(s, FLT_OCD1, I_OCD1, -i >= OCD1_TRIP_A, true, OCD1_DELAY_MS, OC_RECOVER_MS);
    eval(s, FLT_OCD2, I_OCD2, -i >= OCD2_TRIP_A, true, OCD2_DELAY_MS, OC_RECOVER_MS);
    eval(s, FLT_OCC,  I_OCC,   i >= OCC_TRIP_A,  true, OCC_DELAY_MS,  OC_RECOVER_MS);

    /* 硬件短路: 立即锁存, 负载移除 1s 后恢复 */
    eval(s, FLT_HW_SCP, I_HW_SCP, m->hw_scp, !m->load_present, 0, 1000);

    eval(s, FLT_CHG_OT, I_CHG_OT, tc_hi >= CHG_OT_TRIP_DC, tc_hi <= CHG_OT_RECOVER_DC,
         TEMP_DELAY_MS, TEMP_DELAY_MS);
    eval(s, FLT_CHG_UT, I_CHG_UT, tc_lo <= CHG_UT_TRIP_DC, tc_lo >= CHG_UT_RECOVER_DC,
         TEMP_DELAY_MS, TEMP_DELAY_MS);
    eval(s, FLT_DSG_OT, I_DSG_OT, tc_hi >= DSG_OT_TRIP_DC, tc_hi <= DSG_OT_RECOVER_DC,
         TEMP_DELAY_MS, TEMP_DELAY_MS);
    eval(s, FLT_DSG_UT, I_DSG_UT, tc_lo <= DSG_UT_TRIP_DC, tc_lo >= DSG_UT_RECOVER_DC,
         TEMP_DELAY_MS, TEMP_DELAY_MS);
    eval(s, FLT_FET_OT, I_FET_OT, tfet >= FET_OT_TRIP_DC, tfet <= FET_OT_RECOVER_DC,
         TEMP_DELAY_MS, TEMP_DELAY_MS);
}

static void balance(bms_state_t *s, const bms_meas_t *m)
{
    uint16_t vmax = bms_cell_max(m), vmin = bms_cell_min(m);
    uint16_t dv = vmax - vmin;
    int16_t i = m->current_a;

    if (i > -BAL_REST_CURRENT_A && i < BAL_REST_CURRENT_A) {
        if (s->rest_ms < BAL_REST_TIME_MS) s->rest_ms += BMS_TICK_MS;
    } else {
        s->rest_ms = 0;
    }
    bool rested = s->rest_ms >= BAL_REST_TIME_MS;

    bool temp_ok = true;
    for (int k = 0; k < 2; k++)          /* 仅看电芯 NTC, MOSFET 大电流发热不影响均衡 */
        if (m->temp_dc[k] < BAL_MIN_TEMP_DC || m->temp_dc[k] > BAL_MAX_TEMP_DC)
            temp_ok = false;
    /* 过压时均衡正好有用, 其他任何故障都停止均衡 */
    bool fault_ok = (s->faults & ~(uint32_t)FLT_CELL_OV) == 0;
    /* 开关电容的电流随压差增大：压差异常大或电芯过低时不开 */
    bool range_ok = dv <= BAL_MAX_DIFF_MV && vmin >= BAL_MIN_CELL_MV;

    bool top = vmax >= BAL_TOP_START_MV;
    /* 静置触发的均衡一旦有电流立即退出; 顶部触发的均衡带电压迟滞退出 */
    bool region_ok = !s->bal_session ? top || rested
                   : s->bal_rest_mode ? rested
                   : vmax + BAL_TOP_HYST_MV >= BAL_TOP_START_MV;

    if (!temp_ok || !fault_ok || !range_ok || !region_ok) {
        s->bal_session = false;
    } else if (s->bal_session) {
        if (dv <= BAL_DIFF_STOP_MV) s->bal_session = false;
    } else if (top && dv >= BAL_DIFF_START_MV) {
        s->bal_session = true;
        s->bal_rest_mode = false;
    } else if (rested && dv >= BAL_REST_DIFF_START_MV) {
        s->bal_session = true;
        s->bal_rest_mode = true;
    }

    /* 被动微调: 主动均衡未运行、处于顶部区间; 相邻两节不同时放电 */
    s->passive_mask = 0;
    if (!s->bal_session && temp_ok && fault_ok && top && dv >= BAL_PASSIVE_MIN_MV) {
        for (int k = 0; k < BMS_CELLS; k++) {
            bool prev = k > 0 && (s->passive_mask & (1u << (k - 1)));
            if (!prev && m->cell_mv[k] >= vmin + BAL_PASSIVE_MIN_MV)
                s->passive_mask |= 1u << k;
        }
    }
}

bms_out_t bms_step(bms_state_t *s, const bms_meas_t *m)
{
    protect(s, m);
    balance(s, m);

    bms_out_t o;
    o.faults = s->faults;
    o.chg_fet = !(s->faults & FLT_BLOCK_CHG);
    o.dsg_fet = !(s->faults & FLT_BLOCK_DSG);

    /* 单向故障时, 若电流正流向允许方向, 打开被禁 FET, 避免 200A 走体二极管 */
    if (s->faults == FLT_CELL_OV && m->current_a <= -2) o.chg_fet = true;
    if (s->faults == FLT_CELL_UV && m->current_a >= 2)  o.dsg_fet = true;

    o.bal_clk = s->bal_session;
    o.passive_mask = s->passive_mask;
    return o;
}
