#include "framework.h"
#include "TrayIcon.h"
#include "AppMessages.h"
#include "resource.h"

static const UINT TRAY_ICON_ID = 1;

bool CreateTrayIcon(HWND hWnd, HICON hIcon) {
    NOTIFYICONDATA nid{};
    nid.cbSize = sizeof(nid);
    nid.hWnd = hWnd;
    nid.uID = TRAY_ICON_ID;
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
    nid.uCallbackMessage = WM_APP_TRAYICON;
    nid.hIcon = hIcon;
    lstrcpynW(nid.szTip, L"BetterAdvancedPaste", ARRAYSIZE(nid.szTip));
    return Shell_NotifyIcon(NIM_ADD, &nid) == TRUE;
}

void RemoveTrayIcon(HWND hWnd) {
    NOTIFYICONDATA nid{};
    nid.cbSize = sizeof(nid);
    nid.hWnd = hWnd;
    nid.uID = TRAY_ICON_ID;
    Shell_NotifyIcon(NIM_DELETE, &nid);
}

void ShowTrayMenu(HWND hWnd) {
    POINT pt; GetCursorPos(&pt);
    HMENU hMenu = CreatePopupMenu();
    if(!hMenu) return;
    InsertMenu(hMenu, -1, MF_BYPOSITION | MF_STRING, ID_TRAY_OPEN_CONFIG, L"Open config file");
    InsertMenu(hMenu, -1, MF_BYPOSITION | MF_STRING, ID_TRAY_ABOUT, L"About");
    InsertMenu(hMenu, -1, MF_BYPOSITION | MF_STRING, ID_TRAY_EXIT, L"Exit");
    SetForegroundWindow(hWnd);
    TrackPopupMenu(hMenu, TPM_BOTTOMALIGN | TPM_LEFTALIGN, pt.x, pt.y, 0, hWnd, nullptr);
    DestroyMenu(hMenu);
}
