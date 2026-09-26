/*
 * 8S LiFePO4 200A BMS —— 保护与均衡参数
 * 单位: 电压 mV, 电流 A(充电为正, 放电为负), 温度 0.1°C, 时间 ms
 *
 * 注意: 短路(SCP)与一级过流由 MP2797 硬件比较器完成(µs 级),
 *       这里的软件阈值是 MCU 侧的二级/慢速保护, 必须比硬件阈值更"宽松"
 *       或与之一致, 不能依赖软件做短路保护。
 */
#ifndef BMS_CONFIG_H
#define BMS_CONFIG_H

#define BMS_CELLS               8
#define BMS_NTC_CH              4   /* 0:电芯1 1:电芯2 2:MOSFET 3:分流器/环境 */
#define BMS_TICK_MS             100

/* ---- 单体电压 ---- */
#define CELL_OV_ALARM_MV        3600
#define CELL_OV_TRIP_MV         3650
#define CELL_OV_RECOVER_MV      3400
#define CELL_OV_DELAY_MS        1000

#define CELL_UV_ALARM_MV        2800
#define CELL_UV_TRIP_MV         2500
#define CELL_UV_RECOVER_MV      2900
#define CELL_UV_DELAY_MS        1000

#define CELL_DIFF_ALARM_MV      300

/* ---- 电流 (软件二级, 硬件 SCP=800A/200us, OCD 硬件=400A/10ms 在 MP2797 寄存器中配置) ---- */
#define OCD1_TRIP_A             220     /* 持续放电上限 200A + 10% */
#define OCD1_DELAY_MS           10000
#define OCD2_TRIP_A             300
#define OCD2_DELAY_MS           1000
#define OCC_TRIP_A              110     /* 持续充电上限 100A + 10% */
#define OCC_DELAY_MS            3000
#define OC_RECOVER_MS           30000   /* 过流后自动重试间隔, 或负载移除 */

/* ---- 温度 (0.1°C) ---- */
#define CHG_OT_TRIP_DC          550
#define CHG_OT_RECOVER_DC       500
#define CHG_UT_TRIP_DC          0       /* LFP 0°C 以下禁止充电(析锂) */
#define CHG_UT_RECOVER_DC       50
#define DSG_OT_TRIP_DC          650
#define DSG_OT_RECOVER_DC       550
#define DSG_UT_TRIP_DC          (-200)
#define DSG_UT_RECOVER_DC       (-150)
#define FET_OT_TRIP_DC          1000
#define FET_OT_RECOVER_DC       800
#define TEMP_DELAY_MS           2000

/* ---- 均衡 (MP2643 x7 相邻对主动均衡 + MP2797 被动补充) ---- */
#define BAL_PAIRS               (BMS_CELLS - 1)   /* 第 k 对 = 芯片 U(k+1)：下节 cell k, 上节 cell k+1 */
#define BAL_TOP_START_MV        3400    /* LFP 平台区电压差不能反映 SOC 差, 只在顶部均衡 */
#define BAL_DIFF_START_MV       30
#define BAL_DIFF_STOP_MV        10
#define BAL_REST_DIFF_START_MV  80      /* 静置时平台区也允许均衡, 但门槛更高 */
#define BAL_REST_CURRENT_A      2       /* |I| 小于此值且持续 REST_TIME 视为静置 */
#define BAL_REST_TIME_MS        1800000 /* 30 min */
#define BAL_MIN_TEMP_DC         0
#define BAL_MAX_TEMP_DC         500
#define BAL_PASSIVE_MIN_MV      5       /* 主动未运行时, 高于 min+5mV 的电芯由 MP2797 被动放电微调 */
#define BAL_TOP_HYST_MV         50      /* 顶部均衡退出迟滞 */
/* 相邻对的启停门限：按「边界以上各节相对均值的电压超出之和」判断，
 * 即要让整组拉平、必须穿过这条边界的电荷量（折算成 mV·节） */
#define BAL_PAIR_START_MV       8
#define BAL_PAIR_STOP_MV        3

#endif
