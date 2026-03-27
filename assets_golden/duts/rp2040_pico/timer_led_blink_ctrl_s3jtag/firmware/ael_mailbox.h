#ifndef AEL_MAILBOX_H
#define AEL_MAILBOX_H

#include <stdint.h>

#define AEL_MAILBOX_MAGIC    0xAE100001u
#ifndef AEL_MAILBOX_ADDR
#define AEL_MAILBOX_ADDR     0x20041F00u
#endif

#define AEL_STATUS_EMPTY     0u
#define AEL_STATUS_RUNNING   1u
#define AEL_STATUS_PASS      2u
#define AEL_STATUS_FAIL      3u

/*
 * Bidirectional mailbox layout
 *
 * firmware → PC  (read-only from PC side):
 *   magic       always 0xAE100001
 *   status      AEL_STATUS_*
 *   error_code  non-zero on FAIL
 *   detail0     bit[0]       = current led_state (1=ON, 0=OFF)
 *               bits[15:1]   = toggle_count (wraps at 32767)
 *               bits[31:16]  = active half-period in ms
 *
 * PC → firmware  (write from PC via GDB: set {int}0x20041F10 = <ms>):
 *   cmd_period_ms  0 = no change
 *                  1..65535 = request new half-period (clamped to 50–5000 ms)
 *                  firmware clears this field after applying the command
 */
typedef struct {
    uint32_t magic;          /* 0: 0xAE100001 — written once at init         */
    uint32_t status;         /* 4: AEL_STATUS_*                              */
    uint32_t error_code;     /* 8: failure detail                            */
    uint32_t detail0;        /* C: led_state | toggle_count<<1 | period<<16  */
    uint32_t cmd_period_ms;  /* 10: PC→firmware command (cleared on apply)   */
} ael_mailbox_t;

#define AEL_MAILBOX  ((volatile ael_mailbox_t *)AEL_MAILBOX_ADDR)

static inline void ael_mailbox_init(void) {
    AEL_MAILBOX->error_code    = 0u;
    AEL_MAILBOX->detail0       = 0u;
    AEL_MAILBOX->cmd_period_ms = 0u;
    AEL_MAILBOX->magic         = AEL_MAILBOX_MAGIC;
    AEL_MAILBOX->status        = AEL_STATUS_RUNNING;
}

static inline void ael_mailbox_fail(uint32_t error_code, uint32_t detail) {
    AEL_MAILBOX->error_code = error_code;
    AEL_MAILBOX->detail0    = detail;
    AEL_MAILBOX->status     = AEL_STATUS_FAIL;
}

#endif /* AEL_MAILBOX_H */
