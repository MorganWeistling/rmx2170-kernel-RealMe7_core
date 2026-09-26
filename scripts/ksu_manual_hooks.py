#!/usr/bin/env python3
"""Insert KernelSU-Next manual (non-kprobe) hooks into a non-GKI kernel tree.

KSU-Next's `next` branch kprobe hook uses `syscall_fn_t`, which arm64 gained
around 4.19 and this 4.14 tree lacks. So we disable the kprobe hook and add the
documented manual hook call sites instead (kernelsu.org non-GKI guide).

Run from the kernel source root. Idempotent.
"""
import re
import sys

# (path, anchor substring identifying the target function's signature,
#  extern declarations block, call code to insert at the top of the body)
HOOKS = [
    # prctl is KernelSU's manager<->kernel command channel. Without this hook
    # (in non-kprobe mode) the manager can't talk to the kernel and hangs on
    # launch. ksu_handle_prctl checks for the KERNEL_SU_OPTION magic itself.
    ("kernel/sys.c",
     "SYSCALL_DEFINE5(prctl, int, option, unsigned long, arg2, unsigned long, arg3,",
     """#ifdef CONFIG_KSU
extern int ksu_handle_prctl(int option, unsigned long arg2, unsigned long arg3,
			unsigned long arg4, unsigned long arg5);
#endif
""",
     """#ifdef CONFIG_KSU
	ksu_handle_prctl(option, arg2, arg3, arg4, arg5);
#endif
"""),
    ("fs/exec.c",
     "static int do_execveat_common(int fd, struct filename *filename,",
     """#ifdef CONFIG_KSU
extern bool ksu_execveat_hook __read_mostly;
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv,
			void *envp, int *flags);
extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,
				 void *argv, void *envp, int *flags);
#endif
""",
     """#ifdef CONFIG_KSU
	if (unlikely(ksu_execveat_hook))
		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
	else
		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
#endif
"""),
    ("fs/open.c",
     "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)",
     """#ifdef CONFIG_KSU
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode,
			 int *flags);
#endif
""",
     """#ifdef CONFIG_KSU
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif
"""),
    ("fs/read_write.c",
     "ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)",
     """#ifdef CONFIG_KSU
extern bool ksu_vfs_read_hook __read_mostly;
extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,
			size_t *count_ptr, loff_t **pos);
#endif
""",
     """#ifdef CONFIG_KSU
	if (unlikely(ksu_vfs_read_hook))
		ksu_handle_vfs_read(&file, &buf, &count, &pos);
#endif
"""),
    ("fs/stat.c",
     "int vfs_statx(int dfd, const char __user *filename, int flags,",
     """#ifdef CONFIG_KSU
extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
#endif
""",
     """#ifdef CONFIG_KSU
	ksu_handle_stat(&dfd, &filename, &flags);
#endif
"""),
    ("drivers/input/input.c",
     "static void input_handle_event(struct input_dev *dev,",
     """#ifdef CONFIG_KSU
extern bool ksu_input_hook __read_mostly;
extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);
#endif
""",
     """#ifdef CONFIG_KSU
	if (unlikely(ksu_input_hook))
		ksu_handle_input_handle_event(&type, &code, &value);
#endif
"""),
]


def insert_externs(lines, decls):
    # after the last top-level #include
    last = -1
    for i, ln in enumerate(lines):
        if ln.startswith("#include"):
            last = i
    if last < 0:
        raise RuntimeError("no #include found")
    return lines[: last + 1] + ["\n"] + decls.splitlines(keepends=True) + lines[last + 1:]


def insert_call(lines, anchor, call):
    # find the anchor line, then the next line that is exactly "{"
    for i, ln in enumerate(lines):
        if anchor in ln:
            j = i
            while j < len(lines) and lines[j].strip() != "{":
                j += 1
            if j >= len(lines):
                raise RuntimeError("no opening brace after anchor: " + anchor)
            return lines[: j + 1] + call.splitlines(keepends=True) + lines[j + 1:]
    raise RuntimeError("anchor not found: " + anchor)


def main():
    failed = []
    for path, anchor, decls, call in HOOKS:
        try:
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
                text = f.read()
        except FileNotFoundError:
            failed.append(path + " (missing)")
            continue
        if "ksu_handle_" in text:
            print("[=] %s already hooked, skipping" % path)
            continue
        lines = text.splitlines(keepends=True)
        try:
            lines = insert_externs(lines, decls)
            lines = insert_call(lines, anchor, call)
        except RuntimeError as e:
            failed.append("%s (%s)" % (path, e))
            continue
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write("".join(lines))
        print("[+] hooked %s" % path)
    if failed:
        print("::error::manual hook insertion failed:")
        for f in failed:
            print("  - " + f)
        sys.exit(1)
    print("All manual hooks inserted.")


if __name__ == "__main__":
    main()
