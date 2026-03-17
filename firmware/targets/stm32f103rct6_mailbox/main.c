/*
 * STM32F103RCT6 — AEL basic mailbox test
 *
 * Observable behaviour:
 *   - Writes mailbox PASS immediately after init
 *   - detail0 increments in idle loop
 *
 * Mailbox address: 0x2000BC00 (SRAM 48 KB top -1 KB)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

int main(void)
{
    ael_mailbox_init();
    ael_mailbox_pass();

    while (1) {
        AEL_MAILBOX->detail0++;
        for (volatile uint32_t d = 0; d < 4000U; d++) __asm__ volatile ("nop");
    }

    return 0;
}
