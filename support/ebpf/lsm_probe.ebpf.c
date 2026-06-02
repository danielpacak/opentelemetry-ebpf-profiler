#include "bpfdefs.h"
#include "tracemgmt.h"
#include "types.h"

// lsm_progs maps from a program ID to an LSM eBPF program. It mirrors perf_progs
// and kprobe_progs but holds LSM-typed unwinders, since a BPF_MAP_TYPE_PROG_ARRAY
// only accepts tail-call targets that share the entry program's type.
struct lsm_progs_t {
  __uint(type, BPF_MAP_TYPE_PROG_ARRAY);
  __type(key, u32);
  __type(value, u32);
  __uint(max_entries, NUM_TRACER_PROGS);
} lsm_progs SEC(".maps");

// LSM_PROBE_ENTRY defines an entry point for LSM based profiling on the given
// hook. It captures the stack of the task triggering the hook and always allows
// the operation (returns 0). The LSM context is not a struct pt_regs, so the
// user-mode registers are resolved from the current task by passing NULL.
#define LSM_PROBE_ENTRY(hook)                                                                       \
  SEC("lsm/" #hook)                                                                                 \
  int lsm__##hook(void *ctx)                                                                        \
  {                                                                                                 \
    u64 pid_tgid = bpf_get_current_pid_tgid();                                                      \
    u32 pid      = pid_tgid >> 32;                                                                  \
    u32 tid      = pid_tgid & 0xFFFFFFFF;                                                            \
                                                                                                    \
    if (pid == 0 || tid == 0) {                                                                     \
      return 0;                                                                                      \
    }                                                                                               \
                                                                                                    \
    u64 ts = bpf_ktime_get_ns();                                                                    \
                                                                                                    \
    collect_trace_ctx(ctx, NULL, TRACE_PROBE, pid, tid, ts, 0);                                     \
    return 0;                                                                                        \
  }

LSM_PROBE_ENTRY(file_open)
LSM_PROBE_ENTRY(task_alloc)

// lsm__dummy is never loaded or called. It just makes sure lsm_progs is
// referenced and keeps the compiler and linker happy.
SEC("lsm/file_open")
int lsm__dummy(void *ctx)
{
  bpf_tail_call(ctx, &lsm_progs, 0);
  return 0;
}
