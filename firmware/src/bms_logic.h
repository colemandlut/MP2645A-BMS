/*
 * 与硬件无关的保护 / 均衡决策逻辑。可在 PC 上单元测试。
 * 由主循环每 BMS_TICK_MS 调用一次 bms_step()。
 */
#ifndef BMS_LOGIC_H
#define BMS_LOGIC_H

#include <stdbool.h>
#include <stdint.h>
#include "bms_config.h"

typedef struct {
    uint16_t cell_mv[BMS_CELLS];
    int16_t  current_a;                /* 充电为正 */
    int16_t  temp_dc[BMS_NTC_CH];
    bool     hw_scp;                   /* MP2797 报告的硬件短路/过流事件 */
    bool     load_present;             /* 负载检测 (放电过流后恢复用) */
} bms_meas_t;

enum {
    FLT_CELL_OV  = 1u << 0,
    FLT_CELL_UV  = 1u << 1,
    FLT_OCD1     = 1u << 2,
    FLT_OCD2     = 1u << 3,
    FLT_OCC      = 1u << 4,
    FLT_CHG_OT   = 1u << 5,
    FLT_CHG_UT   = 1u << 6,
    FLT_DSG_OT   = 1u << 7,
    FLT_DSG_UT   = 1u << 8,
    FLT_FET_OT   = 1u << 9,
    FLT_HW_SCP   = 1u << 10,
};

/* 阻止充电 / 阻止放电 的故障集合 */
#define FLT_BLOCK_CHG (FLT_CELL_OV | FLT_OCC | FLT_CHG_OT | FLT_CHG_UT | FLT_FET_OT | FLT_HW_SCP)
#define FLT_BLOCK_DSG (FLT_CELL_UV | FLT_OCD1 | FLT_OCD2 | FLT_DSG_OT | FLT_DSG_UT | FLT_FET_OT | FLT_HW_SCP)

typedef struct {
    uint32_t faults;
    uint32_t tmr[16];                  /* 每个故障位的去抖/恢复计时 */
    uint32_t rest_ms;
    bool     active_bal;               /* MP2645A EN 引脚 */
    bool     bal_rest_mode;            /* 本次均衡由静置条件触发 */
    uint8_t  passive_mask;             /* MP2797 内部被动均衡位图 */
} bms_state_t;

typedef struct {
    bool     chg_fet;
    bool     dsg_fet;
    bool     active_bal;
    uint8_t  passive_mask;
    uint32_t faults;
} bms_out_t;

void      bms_init(bms_state_t *s);
bms_out_t bms_step(bms_state_t *s, const bms_meas_t *m);

uint16_t  bms_cell_max(const bms_meas_t *m);
uint16_t  bms_cell_min(const bms_meas_t *m);

#endif
