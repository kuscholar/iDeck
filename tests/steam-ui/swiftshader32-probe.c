/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Minimal Vulkan 1.0 ABI declarations for an official, unmodified Win32 ICD.
 * No CEF, network, account data, renderer replacement or exception suppression. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
typedef void *VkInstance;
typedef void *VkPhysicalDevice;
typedef void *VkDevice;
typedef struct {
    uint32_t type; const void *next; uint32_t flags;
    const void *app; uint32_t layers; const char *const *layer_names;
    uint32_t extensions; const char *const *extension_names;
} InstanceInfo;
typedef struct {
    uint32_t type; const void *next; uint32_t flags, family, count; const float *priorities;
} QueueInfo;
typedef struct {
    uint32_t type; const void *next; uint32_t flags, queues; const QueueInfo *queue_infos;
    uint32_t layers; const char *const *layer_names;
    uint32_t extensions; const char *const *extension_names; const void *features;
} DeviceInfo;
typedef struct { uint32_t flags,count,timestamp,granularity[3]; } QueueProperties;
typedef void (WINAPI *VoidFunction)(void);
typedef VoidFunction (WINAPI *GetProc)(VkInstance,const char *);
typedef int32_t (WINAPI *CreateInstance)(const InstanceInfo *,const void *,VkInstance *);
typedef int32_t (WINAPI *Enumerate)(VkInstance,uint32_t *,VkPhysicalDevice *);
typedef void (WINAPI *GetQueues)(VkPhysicalDevice,uint32_t *,QueueProperties *);
typedef int32_t (WINAPI *CreateDevice)(VkPhysicalDevice,const DeviceInfo *,const void *,VkDevice *);
typedef void (WINAPI *DestroyDevice)(VkDevice,const void *);
typedef void (WINAPI *DestroyInstance)(VkInstance,const void *);
_Static_assert(sizeof(void *)==4,"i386 required");
_Static_assert(sizeof(InstanceInfo)==32 && sizeof(QueueInfo)==24 && sizeof(DeviceInfo)==40,"Vulkan Win32 ABI");
static FILE *out;
static LONG CALLBACK observe(EXCEPTION_POINTERS *e) {
    DWORD code=e->ExceptionRecord->ExceptionCode;
    if(out && (code==0xe06d7363 || code==EXCEPTION_ACCESS_VIOLATION)) {
        fprintf(out,"observed_exception=%08lx (not suppressed)\n",code);fflush(out);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
static void finish(void) { FILE *stream=out; out=NULL; if(stream)fclose(stream); }
int main(void) {
    const char *dir="C:\\Steam32BundleLab\\bin\\cef\\cef.win7";
    HMODULE dll;GetProc get;CreateInstance create;Enumerate enumerate;
    GetQueues queues;CreateDevice device_create;DestroyInstance destroy;
    VkInstance instance=NULL;VkDevice device=NULL;VkPhysicalDevice physical[8];
    QueueProperties properties[32];uint32_t count=8,n=32,i;int32_t result;
    InstanceInfo info={1,NULL,0,NULL,0,NULL,0,NULL};
    float priority=1.0f;QueueInfo queue={2,NULL,0,0,1,&priority};
    DeviceInfo device_info={3,NULL,0,1,&queue,0,NULL,0,NULL,NULL};
    out=fopen("C:\\madeira-swiftshader32-results.txt","w");if(!out)return 90;
    fprintf(out,"swiftshader32 begin pid=%lu\n",GetCurrentProcessId());fflush(out);
    AddVectoredExceptionHandler(1,observe);
    SetDllDirectoryA(dir);
    dll=LoadLibraryA("C:\\Steam32BundleLab\\bin\\cef\\cef.win7\\vk_swiftshader.dll");
    if(!dll){fprintf(out,"FAIL LoadLibrary error=%lu\n",GetLastError());finish();return 1;}
    get=(GetProc)GetProcAddress(dll,"vk_icdGetInstanceProcAddr");
    if(!get)get=(GetProc)GetProcAddress(dll,"vkGetInstanceProcAddr");
    if(!get){fprintf(out,"FAIL ICD export\n");finish();return 2;}
    create=(CreateInstance)get(NULL,"vkCreateInstance");
    if(!create){fprintf(out,"FAIL create export\n");finish();return 3;}
    fprintf(out,"before vkCreateInstance\n");fflush(out);
    result=create(&info,NULL,&instance);fprintf(out,"vkCreateInstance=%ld\n",(long)result);fflush(out);
    if(result){finish();return 4;}
    enumerate=(Enumerate)get(instance,"vkEnumeratePhysicalDevices");
    queues=(GetQueues)get(instance,"vkGetPhysicalDeviceQueueFamilyProperties");
    device_create=(CreateDevice)get(instance,"vkCreateDevice");
    destroy=(DestroyInstance)get(instance,"vkDestroyInstance");
    if(!enumerate||!queues||!device_create||!destroy){fprintf(out,"FAIL instance exports\n");finish();return 5;}
    result=enumerate(instance,&count,physical);
    fprintf(out,"enumerate=%ld physical_count=%u\n",(long)result,count);fflush(out);
    if(result||!count||count>8){finish();return 6;}
    queues(physical[0],&n,NULL);
    if(!n||n>32){fprintf(out,"FAIL queue count=%u\n",n);finish();return 7;}
    queues(physical[0],&n,properties);
    if(!n||n>32){fprintf(out,"FAIL queue count=%u\n",n);finish();return 7;}
    for(i=0;i<n;i++)if(properties[i].count){queue.family=i;break;}
    if(i==n){fprintf(out,"FAIL no queue\n");finish();return 8;}
    fprintf(out,"before vkCreateDevice family=%u\n",i);fflush(out);
    result=device_create(physical[0],&device_info,NULL,&device);
    fprintf(out,"vkCreateDevice=%ld\n",(long)result);fflush(out);
    if(!result){
        DestroyDevice device_destroy=(DestroyDevice)get(instance,"vkDestroyDevice");
        if(device_destroy)device_destroy(device,NULL);
    }
    destroy(instance,NULL);
    fprintf(out,"%s\n",result?"FAIL":"PASS");finish();return result?9:0;
}
