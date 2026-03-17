#ifndef AEL_MAILBOX_H
#define AEL_MAILBOX_H

#include <stdint.h>

/*
 * AEL Debug Mailbox — STM32F103RCT6
 *
 * SRAM: 48 KB (0x20000000–0x2000BFFF)
 * Mailbox at 0x2000BC00 (1 KB below SRAM end).
 */

#define AEL_MAILBOX_MAGIC    0xAE100001u
#ifndef AEL_MAILBOX_ADDR
#define AEL_MAILBOX_ADDR     0x2000BC00u
#endif

#define AEL_STATUS_EMPTY     0u
#define AEL_STATUS_RUNNING   1u
#define AEL_STATUS_PASS      2u
#define AEL_STATUS_FAIL      3u

typedef struct {
    uint32_t magic;
    uint32_t status;
    uint32_t error_code;
    uint32_t detail0;
} ael_mailbox_t;

#define AEL_MAILBOX  ((volatile ael_mailbox_t *)AEL_MAILBOX_ADDR)

static inline void ael_mailbox_init(void) {
    AEL_MAILBOX->magic      = AEL_MAILBOX_MAGIC;
    AEL_MAILBOX->error_code = 0u;
    AEL_MAILBOX->detail0    = 0u;
    AEL_MAILBOX->status     = AEL_STATUS_RUNNING;
}

static inline void ael_mailbox_pass(void) {
    AEL_MAILBOX->status = AEL_STATUS_PASS;
}

static inline void ael_mailbox_fail(uint32_t error_code, uint32_t detail) {
    AEL_MAILBOX->error_code = error_code;
    AEL_MAILBOX->detail0    = detail;
    AEL_MAILBOX->status     = AEL_STATUS_FAIL;
}

#endif /* AEL_MAILBOX_H */
