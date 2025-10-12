#include "framework.h"
#include "AppMessages.h"
#include "KeyboardHook.h"

static HHOOK g_hHook = nullptr;
static HWND  g_notifyWnd = nullptr;
static bool g_winDown = false;
static bool g_shiftDown = false;
static bool g_vDown = false;
static bool g_fired = false;

static void ResetStateIfAllUp() {
    if(!g_winDown && !g_shiftDown && !g_vDown) {
        g_fired = false; // allow next trigger
    }
}

static LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT* p = reinterpret_cast<KBDLLHOOKSTRUCT*>(lParam);
        bool keyDown = (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN);
        bool keyUp   = (wParam == WM_KEYUP || wParam == WM_SYSKEYUP);

        switch(p->vkCode) {
            case VK_LWIN:
            case VK_RWIN:
                if(keyDown) g_winDown = true; else if(keyUp) g_winDown = false; break;
            case VK_SHIFT:
            case VK_LSHIFT:
            case VK_RSHIFT:
                if(keyDown) g_shiftDown = true; else if(keyUp) g_shiftDown = false; break;
            case 'V':
                if(keyDown) g_vDown = true; else if(keyUp) g_vDown = false; break;
            default: break;
        }

        if(keyDown) {
            if(g_winDown && g_shiftDown && g_vDown && !g_fired) {
                g_fired = true; // debounce
                if(g_notifyWnd) {
                    PostMessage(g_notifyWnd, WM_APP_HOTKEY_TRIGGER, 0, 0);
                }
            }
        }
        if(keyUp) {
            ResetStateIfAllUp();
        }
    }
    return CallNextHookEx(g_hHook, nCode, wParam, lParam);
}

bool InstallKeyboardHook(HINSTANCE hInst, HWND notifyHwnd) {
    if(g_hHook) return true;
    g_notifyWnd = notifyHwnd;
    g_hHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, hInst, 0);
    return g_hHook != nullptr;
}

void UninstallKeyboardHook() {
    if(g_hHook) {
        UnhookWindowsHookEx(g_hHook);
        g_hHook = nullptr;
    }
    g_notifyWnd = nullptr;
}
