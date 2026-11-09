/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeKernelLog.h"
#include <pthread.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/resource.h>
#include <stdatomic.h>
#include <stdint.h>
#if IDECK_LAB_NATIVE_LOG
/* Exact pinned public diagnostic globals. Independent atomic observations,
 * not coherent VM ownership, physical accounting or permission for handoff. */
extern _Atomic long anon_page_count;
extern _Atomic uint64_t asbestos_stat_instances,asbestos_stat_blocks,asbestos_stat_code_words;
extern _Atomic uint64_t asbestos_stat_idle_flushes,asbestos_stat_cap_flushes,asbestos_stat_pressure_flushes;
#endif
#ifdef __APPLE__
#include <TargetConditionals.h>
#include <mach/mach.h>
#include <mach/task_info.h>
#if TARGET_OS_IPHONE
#include <os/proc.h>
#endif
#endif
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static int attempted,fd=-1,saturated;
static size_t bytes;
static char filename[96];
static int write_all(const char *body,size_t length){
    size_t offset=0;
    while(offset<length){ssize_t n=write(fd,body+offset,length-offset);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return -EIO;
        offset+=(size_t)n;bytes+=(size_t)n;
    }
    return 0;
}
int ideck_native_log_start(const char *directory){
    if(!directory||directory[0]!='/')return -EINVAL;
    pthread_mutex_lock(&lock);
    if(attempted){pthread_mutex_unlock(&lock);return -EBUSY;}
    attempted=1;int error=0;
    int dir=open(directory,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(dir<0){error=-errno;goto done;}
    struct stat st;
    if(fstat(dir,&st)||!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()||(st.st_mode&0077)){
        error=-EPERM;close(dir);goto done;
    }
    struct timespec now;
    if(clock_gettime(CLOCK_MONOTONIC,&now)){error=-errno;close(dir);goto done;}
    int length=snprintf(filename,sizeof filename,"kernel-%ld-%lld-%ld.log",(long)getpid(),(long long)now.tv_sec,now.tv_nsec);
    if(length<0||(size_t)length>=sizeof filename){error=-ENAMETOOLONG;close(dir);goto done;}
    fd=openat(dir,filename,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);error=fd<0?-errno:0;close(dir);
    if(!error){const char header[]="IDECK_NATIVE_KERNEL_LOG_V1 private native kernel diagnostics; input tracing disabled\n";error=write_all(header,sizeof header-1);}
done:
    if(error&&fd>=0){close(fd);fd=-1;}
    if(error)filename[0]=0;
    pthread_mutex_unlock(&lock);return error;
}
const char *ideck_native_log_name(void){pthread_mutex_lock(&lock);const char *name=filename[0]?filename:NULL;pthread_mutex_unlock(&lock);return name;}
size_t ideck_native_log_bytes(void){pthread_mutex_lock(&lock);size_t n=bytes;pthread_mutex_unlock(&lock);return n;}
void ideck_native_log_line(const char *line){
    if(!line)return;
    pthread_mutex_lock(&lock);
    if(fd<0||saturated){pthread_mutex_unlock(&lock);return;}
    size_t size=strnlen(line,4097);
    if(size>4096){line="native_line_omitted oversized";size=strlen(line);}
    /* This sink receives kernel messages, not Steam stdout or input callbacks.
     * Omit suspect authentication/argv diagnostics wholesale; raw artifacts
     * still remain private, never suitable for public log attachment. */
    const char *sensitive[]={"password","passwd","token","secret","ticket","cookie","credential","authorization","bearer","login_key","steamid","argv"};
    for(unsigned i=0;i<sizeof sensitive/sizeof sensitive[0];i++)if(strcasestr(line,sensitive[i])){
        line="native_line_omitted sensitive";size=strlen(line);break;
    }
    const char capped[]="native_log_capacity_reached\n";
    if(bytes>IDECK_NATIVE_LOG_LIMIT||size+1+sizeof capped-1>IDECK_NATIVE_LOG_LIMIT-bytes){
        if(bytes+sizeof capped-1<=IDECK_NATIVE_LOG_LIMIT)write_all(capped,sizeof capped-1);
        saturated=1;
    }else if(write_all(line,size)||write_all("\n",1)){saturated=1;}
    pthread_mutex_unlock(&lock);
}
void ideck_native_log_resources(void){
    pthread_mutex_lock(&lock);int active=fd>=0&&!saturated;pthread_mutex_unlock(&lock);
    if(!active)return;
#ifdef __APPLE__
    struct timespec now;if(clock_gettime(CLOCK_MONOTONIC,&now))return;
    task_vm_info_data_t info={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
    kern_return_t result=task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&count);
    int valid=result==KERN_SUCCESS&&count>=TASK_VM_INFO_REV1_COUNT;
    size_t available=0;int available_known=0;
#if TARGET_OS_IPHONE
    available=os_proc_available_memory();available_known=1;
#endif
    struct rusage usage={0};int cpu_valid=getrusage(RUSAGE_SELF,&usage)==0;
    uint64_t user_us=cpu_valid?(uint64_t)usage.ru_utime.tv_sec*1000000+usage.ru_utime.tv_usec:0;
    uint64_t system_us=cpu_valid?(uint64_t)usage.ru_stime.tv_sec*1000000+usage.ru_stime.tv_usec:0;
    char row[512];snprintf(row,sizeof row,
        "NATIVE_RESOURCE mono_ms=%llu query_status=%d valid=%d footprint_bytes=%llu resident_bytes=%llu virtual_bytes=%llu available_known=%d available_bytes=%llu cpu_valid=%d cpu_user_us=%llu cpu_system_us=%llu",
        (unsigned long long)now.tv_sec*1000+(unsigned long long)now.tv_nsec/1000000,result,valid,
        valid?(unsigned long long)info.phys_footprint:0,valid?(unsigned long long)info.resident_size:0,
        valid?(unsigned long long)info.virtual_size:0,available_known,(unsigned long long)available,cpu_valid,
        (unsigned long long)user_us,(unsigned long long)system_us);
    ideck_native_log_line(row);
#if IDECK_LAB_NATIVE_LOG
    snprintf(row,sizeof row,
        "LINUX_MEMORY_CLASSES mono_ms=%llu anonymous_guest_pages=%ld translation_tables=%llu translated_blocks=%llu code_words_bytes=%llu idle_flushes=%llu cap_flushes=%llu pressure_flushes=%llu",
        (unsigned long long)now.tv_sec*1000+(unsigned long long)now.tv_nsec/1000000,
        atomic_load_explicit(&anon_page_count,memory_order_relaxed),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_instances,memory_order_relaxed),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_blocks,memory_order_relaxed),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_code_words,memory_order_relaxed)*sizeof(unsigned long),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_idle_flushes,memory_order_relaxed),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_cap_flushes,memory_order_relaxed),
        (unsigned long long)atomic_load_explicit(&asbestos_stat_pressure_flushes,memory_order_relaxed));
    ideck_native_log_line(row);
#endif
#else
    ideck_native_log_line("NATIVE_RESOURCE query_status=unsupported valid=0 available_known=0");
#endif
}
