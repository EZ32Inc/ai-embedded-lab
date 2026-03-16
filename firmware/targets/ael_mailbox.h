#ifndef AEL_MAILBOX_H
#define AEL_MAILBOX_H

#include <stdint.h>

/*
 * AEL Debug Mailbox — shared header for all AEL DUT test firmware
 *
 * Mailbox placed at 0x20007F00 (SRAM end - 256 bytes).
 * Compatible with STM32G431CBU6 (SRAM: 0x20000000, 32 KB).
 * Stack grows down from 0x20008000; 256-byte gap provides safety margin.
 *
 * Read from host:
 *   arm-none-eabi-gdb --batch \
 *     -ex "target extended-remote <ip>:4242" \
 *     -ex "monitor a" -ex "attach 1" \
 *     -ex "x/4xw 0x20007F00" -ex "detach" -ex "quit"
 *
 *   or: python3 tools/read_mailbox.py --ip <ip>
 */

#define AEL_MAILBOX_MAGIC    0xAE100001u
#ifndef AEL_MAILBOX_ADDR
#define AEL_MAILBOX_ADDR     0x20007F00u   /* default: STM32G431CBU6 SRAM end-256 */
#endif

#define AEL_STATUS_EMPTY     0u
#define AEL_STATUS_RUNNING   1u
#define AEL_STATUS_PASS      2u
#define AEL_STATUS_FAIL      3u

typedef struct {
    uint32_t magic;       /* AEL_MAILBOX_MAGIC when valid */
    uint32_t status;      /* AEL_STATUS_xxx — written last */
    uint32_t error_code;  /* 0 = none; test-specific on fail */
    uint32_t detail0;     /* optional diagnostic field */
} ael_mailbox_t;

#define AEL_MAILBOX  ((volatile ael_mailbox_t *)AEL_MAILBOX_ADDR)

static inline void ael_mailbox_init(void) {
    AEL_MAILBOX->magic      = AEL_MAILBOX_MAGIC;
    AEL_MAILBOX->error_code = 0u;
    AEL_MAILBOX->detail0    = 0u;
    AEL_MAILBOX->status     = AEL_STATUS_RUNNING;   /* write status last */
}

static inline void ael_mailbox_pass(void) {
    AEL_MAILBOX->status = AEL_STATUS_PASS;
}

static inline void ael_mailbox_fail(uint32_t error_code, uint32_t detail) {
    AEL_MAILBOX->error_code = error_code;
    AEL_MAILBOX->detail0    = detail;
    AEL_MAILBOX->status     = AEL_STATUS_FAIL;      /* write status last */
}

#endif /* AEL_MAILBOX_H */
