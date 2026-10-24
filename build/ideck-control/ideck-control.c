/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Local, fixed-command helper. No credentials, arbitrary shell commands or kills. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <xinput.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <wchar.h>
#include <wctype.h>
#include <string.h>
#include <ctype.h>
static const char *request_path="C:\\ideck-command.txt",*ack_path="C:\\ideck-command-result.txt";
static void ack(const char *id,const char *result) {
    FILE *f=fopen("C:\\ideck-command-result.tmp","w");if(!f)return;
    fprintf(f,"%s %s\n",id,result);fclose(f);
    MoveFileExA("C:\\ideck-command-result.tmp",ack_path,MOVEFILE_REPLACE_EXISTING);
}
static int read_request(char *id,char *command) {
    FILE *f=fopen(request_path,"r");int ok;if(!f)return 0;
    ok=fscanf(f,"%36s %31s",id,command)==2;fclose(f);
    if(!ok||strlen(id)!=36)return 0;
    for(unsigned i=0;i<36;i++)if(!isxdigit((unsigned char)id[i])&&id[i]!='-')return 0;
    return 1;
}
static int image(DWORD pid,WCHAR *path) {
    HANDLE p=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);DWORD n=1024;
    if(!p)return 0;BOOL ok=QueryFullProcessImageNameW(p,0,path,&n);CloseHandle(p);
    if(!ok)return 0;for(DWORD i=0;i<n;i++)path[i]=towlower(path[i]);return 1;
}
static int game_window(HWND window) {
    DWORD pid=0;WCHAR path[1024];GetWindowThreadProcessId(window,&pid);
    return IsWindowVisible(window)&&image(pid,path)&&wcsstr(path,L"\\steamapps\\common\\")!=NULL;
}
static HWND game;static DWORD game_pid;static int ambiguous;
static BOOL CALLBACK find_game(HWND window,LPARAM unused) {
    (void)unused;if(!game_window(window))return TRUE;
    DWORD pid=0;GetWindowThreadProcessId(window,&pid);
    if(game&&pid!=game_pid){ambiguous=1;return TRUE;}
    if(!game||GetForegroundWindow()==window){game=window;game_pid=pid;}return TRUE;
}
static HWND steam_window;static LONG64 steam_area;
static BOOL CALLBACK find_steam(HWND window,LPARAM unused) {
    (void)unused;DWORD pid;WCHAR path[1024];RECT r;
    if(!IsWindowVisible(window))return TRUE;GetWindowThreadProcessId(window,&pid);
    if(!image(pid,path))return TRUE;
    const WCHAR *name=wcsrchr(path,L'\\');name=name?name+1:path;
    if(wcscmp(name,L"steam.exe")&&wcscmp(name,L"steamwebhelper.exe"))return TRUE;
    if(!GetWindowRect(window,&r))return TRUE;LONG64 area=(LONG64)(r.right-r.left)*(r.bottom-r.top);
    if(area>steam_area){steam_area=area;steam_window=window;}return TRUE;
}
static int open_steam(const WCHAR *url) {
    /* Dispatch a fixed Steam URI to the running client's actual executable,
     * rather than depending on an old prefix's protocol registration. */
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    PROCESSENTRY32W entry={0};entry.dwSize=sizeof(entry);
    if(snapshot!=INVALID_HANDLE_VALUE) {
        BOOL more=Process32FirstW(snapshot,&entry);
        while(more) {
            WCHAR path[1024];
            if(!_wcsicmp(entry.szExeFile,L"steam.exe") && image(entry.th32ProcessID,path)) {
                WCHAR command[1200];STARTUPINFOW startup={0};PROCESS_INFORMATION child={0};
                startup.cb=sizeof(startup);
                int n=swprintf(command,1200,L"\"%ls\" %ls",path,url);
                CloseHandle(snapshot);
                if(n<0||n>=1200)return 0;
                if(!CreateProcessW(path,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&child))return 0;
                CloseHandle(child.hThread);CloseHandle(child.hProcess);return 1;
            }
            more=Process32NextW(snapshot,&entry);
        }
        CloseHandle(snapshot);
    }
    return (INT_PTR)ShellExecuteW(NULL,L"open",url,NULL,NULL,SW_SHOWNORMAL)>32;
}
static int focus_steam(void) {
    steam_window=NULL;steam_area=0;EnumWindows(find_steam,0);
    if(!steam_window)return 0;
    if(IsIconic(steam_window))ShowWindow(steam_window,SW_RESTORE);
    return GetForegroundWindow()==steam_window || SetForegroundWindow(steam_window)!=0;
}
static UINT key(WORD vk,DWORD flags) {
    INPUT input={0};input.type=INPUT_KEYBOARD;input.ki.wVk=vk;
    /* CEF derives KeyboardEvent.code from the Windows scan code. Wine preserves
     * a zero wScan for injected virtual keys; Ctrl+1 then has no Digit1 code. */
    input.ki.wScan=(WORD)MapVirtualKeyW(vk,MAPVK_VK_TO_VSC);
    input.ki.dwFlags=flags;return SendInput(1,&input,sizeof(input));
}
static void focus_status(int focused) {
    FILE *f=fopen("C:\\ideck-focus-status.txt","w");
    if(f){fprintf(f,"startup_focus=%d foreground_matches=%d\n",focused,
        steam_window && GetForegroundWindow()==steam_window);fclose(f);}
}
static void input_status(void) {
    typedef DWORD (WINAPI *GetState)(DWORD,XINPUT_STATE *);
    static GetState get;static int initialized;static unsigned long observed_changes;static XINPUT_GAMEPAD previous_pad;static DWORD last_connected=99,last_buttons=0xffffffffU,last_hid=99;
    if(!initialized){HMODULE dll=LoadLibraryW(L"xinput1_4.dll");get=dll?(GetState)(void *)GetProcAddress(dll,"XInputGetState"):NULL;initialized=1;}
    XINPUT_STATE state={0};DWORD connected=get&&get(0,&state)==ERROR_SUCCESS;
    RAWINPUTDEVICELIST devices[32];UINT count=32;DWORD hid=0;
    UINT read=GetRawInputDeviceList(devices,&count,sizeof(devices[0]));
    if(read!=(UINT)-1)for(UINT i=0;i<read;i++) {
        RID_DEVICE_INFO info={0};UINT size=sizeof(info);info.cbSize=sizeof(info);
        if(devices[i].dwType==RIM_TYPEHID&&GetRawInputDeviceInfoW(devices[i].hDevice,RIDI_DEVICEINFO,&info,&size)!=(UINT)-1&&
           info.hid.usUsagePage==1&&(info.hid.usUsage==4||info.hid.usUsage==5))hid++;
    }
    DWORD buttons=connected?state.Gamepad.wButtons:0;
    int pad_changed=memcmp(&previous_pad,&state.Gamepad,sizeof(previous_pad))!=0;
    if(pad_changed){observed_changes++;previous_pad=state.Gamepad;}
    if(connected!=last_connected||buttons!=last_buttons||hid!=last_hid||pad_changed) {
        FILE *f=fopen("C:\\ideck-input-status.txt","w");
        if(f){fprintf(f,"xinput=%lu buttons=%04lx hid_gamepads=%lu observed_changes=%lu\n",(unsigned long)connected,(unsigned long)buttons,(unsigned long)hid,observed_changes);fclose(f);}
        last_connected=connected;last_buttons=buttons;last_hid=hid;
    }
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR line,int show) {
    (void)instance;(void)previous;(void)line;(void)show;
    HANDLE mutex=CreateMutexW(NULL,FALSE,L"Local\\iDeckControl");
    if(!mutex||GetLastError()==ERROR_ALREADY_EXISTS)return 0;
    char last[37]="",id[37],command[32],pending[37]="";HANDLE exiting=NULL;ULONGLONG deadline=0;
    if(read_request(id,command))strcpy(last,id); /* Never replay a stale action on startup. */
    ack("ready","ready");
    unsigned input_ticks=0;int initial_focus=0;
    for(;;) {
        if(!(input_ticks++%5)) {
            /* Steam is started after this helper. Its first login/browser window
             * must own Windows input before controller/keyboard navigation. Stop
             * activating once successful; never keep stealing focus from games. */
            if(!initial_focus && focus_steam()) { initial_focus=1;focus_status(1); }
            input_status();
        }
        if(exiting) {
            DWORD state=WaitForSingleObject(exiting,0);
            if(state==WAIT_OBJECT_0) {
                CloseHandle(exiting);exiting=NULL;
                int dispatched=open_steam(L"steam://open/bigpicture");Sleep(200);focus_steam();
                ack(pending,dispatched?"returned-to-steam":"steam-open-failed");
            } else if(GetTickCount64()>deadline) {
                CloseHandle(exiting);exiting=NULL;ack(pending,"game-close-pending");
            }
        }
        if(read_request(id,command)&&strcmp(last,id)) {
            strcpy(last,id);
            if(!strcmp(command,"menu")) {
                if(!focus_steam()) { open_steam(L"steam://open/bigpicture");Sleep(300); }
                if(focus_steam()) {
                    UINT sent=key(VK_CONTROL,0);sent+=key('1',0);Sleep(100);sent+=key('1',KEYEVENTF_KEYUP);sent+=key(VK_CONTROL,KEYEVENTF_KEYUP);
                    ack(id,sent==4?"menu-requested":"input-unavailable");
                } else ack(id,"steam-window-unavailable");
            } else if(!strcmp(command,"big-picture")) {
                ack(id,open_steam(L"steam://open/bigpicture")?"big-picture-requested":"steam-open-failed");
            } else if(!strcmp(command,"change-account")) {
                ack(id,open_steam(L"steam://changeuser")?"account-ui-requested":"steam-open-failed");
            } else if(!strcmp(command,"exit-game")) {
                if(exiting){ack(id,"busy");continue;}
                HWND foreground=GetForegroundWindow();game=NULL;game_pid=0;ambiguous=0;
                if(game_window(foreground)){game=foreground;GetWindowThreadProcessId(game,&game_pid);}
                else EnumWindows(find_game,0);
                if(!game||ambiguous){ack(id,ambiguous?"multiple-games":"no-game");continue;}
                exiting=OpenProcess(SYNCHRONIZE,FALSE,game_pid);
                if(!exiting){ack(id,"game-unavailable");continue;}
                if(!PostMessageW(game,WM_CLOSE,0,0)){CloseHandle(exiting);exiting=NULL;ack(id,"close-failed");continue;}
                strcpy(pending,id);deadline=GetTickCount64()+20000;ack(id,"close-requested");
            } else ack(id,"invalid-command");
        }
        Sleep(100);
    }
}
