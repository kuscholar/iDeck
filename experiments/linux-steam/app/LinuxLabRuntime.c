/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LinuxLabRuntime.h"
#include "LabDeviceFS.h"
#include "LaunchProtocol.h"
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/real.h"
#include "fs/devices.h"
#include "fs/dev.h"
#include "fs/fd.h"
#include "fs/path.h"

static atomic_bool consumed;
static atomic_int phase;
const char *ideck_linux_lab_stage(void) {
    static const char *names[] = {"idle", "mount-root", "init-task", "runtime-directories", "device-filesystem", "child-task", "elf-load", "guest-running", "guest-exited"};
    return names[atomic_load(&phase)];
}
static int wait_status = -1;
static struct task *initial_child;
extern int ideck_lab_bridge_install(void);
extern int ideck_lab_bridge_major(void);
extern const char *ideck_linuxrunner_dirfd_guard(void);
void restore_termios(void) {} /* This embedding never configures a host tty. */
static void observe_exit(struct task *task, int status) {
    if (task == initial_child) wait_status = status;
}
static void *run_guest(void *unused) {
    (void)unused;
    current = initial_child;
    current->thread = pthread_self();
    task_run_current();
    return NULL;
}
static int run(const char *root_path, int mode) {
    int steam_probe = mode == 1, compat_probe = mode == 2;
    if (!root_path || root_path[0] != '/') return -22;
    if (atomic_exchange(&consumed, 1)) return -16;
    if (strcmp(ideck_linuxrunner_dirfd_guard(), "IDECK_LINUXRUNNER_DIRFD_GUARD_V3")) return -5;
    atomic_store(&phase, 1);
    int err = mount_root(&realfs, root_path);
    if (err < 0) return err;
    atomic_store(&phase, 2);
    if ((err = become_first_process()) < 0) return err;
    atomic_store(&phase, 3);
    const char *dirs[] = {"/proc", "/tmp", "/root", "/root/.steam", "/dev"};
    for (unsigned i = 0; i < sizeof dirs / sizeof dirs[0]; i++) {
        err = generic_mkdirat(AT_PWD, dirs[i], i == 1 ? 01777 : 0700);
        if (err < 0 && err != -17) return err;
    }
    if ((err = do_mount(&procfs, "proc", "/proc", "", 0)) < 0) return err;
    atomic_store(&phase, 4);
    char devices_path[4096];
    if (lab_device_fs_prepare(root_path, devices_path, sizeof devices_path)) return -5;
    if ((err = do_mount(&fakefs, devices_path, "/dev", "", 0)) < 0) return err;
    const struct { const char *path; int minor; } devices[] = {
        {"/dev/null", DEV_NULL_MINOR}, {"/dev/zero", DEV_ZERO_MINOR},
        {"/dev/random", DEV_RANDOM_MINOR}, {"/dev/urandom", DEV_URANDOM_MINOR}
    };
    for (unsigned i = 0; i < sizeof devices / sizeof devices[0]; i++)
        if ((err = generic_mknodat(AT_PWD, devices[i].path, S_IFCHR | 0666,
                                  dev_make(MEM_MAJOR, devices[i].minor))) < 0) return err;
    if ((err = ideck_lab_bridge_install()) < 0) return err;
    if ((err = generic_mknodat(AT_PWD, "/dev/ideck-madeira", S_IFCHR | 0600,
                              dev_make(ideck_lab_bridge_major(), 0))) < 0) return err;
    if (steam_probe) {
        const char *links[] = {"/root/.steam/steam", "/root/.steam/root"};
        for (unsigned i = 0; i < sizeof links / sizeof links[0]; i++) {
            err = generic_symlinkat("/Steam", AT_PWD, links[i]);
            if (err < 0 && err != -17) return err;
        }
    }
    /* Keep PID 1 out of guest execution: its halt path calls host _exit(). */
    if ((err = prepare_guest_runtime_dirs()) < 0) return err;
    atomic_store(&phase, 5);
    if ((err = become_new_init_child()) < 0) return err;
    initial_child = current;
    if ((err = create_stdio("/dev/null", MEM_MAJOR, DEV_NULL_MINOR)) < 0) return err;
    if (compat_probe) {
        const char *fixture[] = {"/mnt", "/mnt/ideck", "/mnt/ideck/SteamLibrary", "/mnt/ideck/SteamLibrary/steamapps", "/mnt/ideck/SteamLibrary/steamapps/common", "/mnt/ideck/SteamLibrary/steamapps/common/Control"};
        for (unsigned i = 0; i < sizeof fixture / sizeof fixture[0]; i++) {
            err = generic_mkdirat(AT_PWD, fixture[i], 0700);
            if (err < 0 && err != -17) return err;
        }
        struct fd *dir = generic_open(fixture[5], O_RDONLY_ | O_DIRECTORY_, 0);
        if (IS_ERR(dir)) return (int)PTR_ERR(dir);
        fs_chdir(current->fs, dir);
    }
    const char *program = steam_probe ? "/Steam/steamrtarm64/steam" : compat_probe ? "/ideck-madeira" : "/probe";
    const char *args = steam_probe ? "/Steam/steamrtarm64/steam\0-clientbeta\0steamdeck_stable\0-nobigpicture\0" :
        compat_probe ? "/ideck-madeira\0waitforexitandrun\0" IDECK_LAUNCH_ROOT "Control/control.exe\0" : "/probe\0";
    const char env[] = "HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0"
        "LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0";
    const char compat_env[] = "HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0"
        "STEAM_COMPAT_APP_ID=480\0STEAM_COMPAT_INSTALL_PATH=" IDECK_LAUNCH_ROOT "Control\0";
    if (steam_probe) {
        struct fd *output = generic_open("/loader-probe-output.txt", O_WRONLY_ | O_CREAT_ | O_TRUNC_, 0600);
        if (IS_ERR(output)) return (int)PTR_ERR(output);
        fd_close(current->files->files[1]);
        fd_close(current->files->files[2]);
        current->files->files[1] = output;
        current->files->files[2] = fd_retain(output);
    }
    atomic_store(&phase, 6);
    if ((err = do_execve(program, steam_probe ? 4 : compat_probe ? 3 : 1, args, compat_probe ? compat_env : env)) < 0) return err;
    exit_hook = observe_exit;
    current = NULL;
    pthread_t worker;
    atomic_store(&phase, 7);
    if ((err = pthread_create(&worker, NULL, run_guest, NULL))) return -err;
    if ((err = pthread_join(worker, NULL))) return -err;
    atomic_store(&phase, 8);
    return wait_status;
}
int ideck_linux_lab_run(const char *root_path) { return run(root_path, 0); }
int ideck_linux_lab_steam_probe(const char *root_path) { return run(root_path, 1); }
int ideck_linux_lab_compat_probe(const char *root_path) { return run(root_path, 2); }
