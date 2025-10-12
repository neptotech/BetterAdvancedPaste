// BetterAdvancedPaste.cpp : Defines the entry point for the application.
//

#include "framework.h"
#include "BetterAdvancedPaste.h"
#include "AppMessages.h"
#include "KeyboardHook.h"
#include "ExplorerDetect.h"
#include "Alert.h"
#include "TrayIcon.h"
#include <string>
#include <shlwapi.h>
#include <shellapi.h>
#pragma comment(lib, "shlwapi.lib")

#define MAX_LOADSTRING 100

// Global Variables:
HINSTANCE hInst;                                // current instance
WCHAR szTitle[MAX_LOADSTRING];                  // The title bar text
WCHAR szWindowClass[MAX_LOADSTRING];            // the main window class name
static HWND g_hMainWnd = nullptr;

// Forward declarations of functions included in this code module:
ATOM                MyRegisterClass(HINSTANCE hInstance);
BOOL                InitInstance(HINSTANCE, int);
LRESULT CALLBACK    WndProc(HWND, UINT, WPARAM, LPARAM);
INT_PTR CALLBACK    About(HWND, UINT, WPARAM, LPARAM);
static void EnsureRunAtStartup();
static void LaunchBetterAdvancedPasteCLI(const std::wstring& folderPath);
static void OpenConfigFile();

// About dialog hyperlink support
static HFONT    g_LinkFont = nullptr;
static HWND     g_hLink = nullptr;
static bool     g_LinkHover = false;
static WNDPROC  g_OldLinkProc = nullptr;
static LRESULT CALLBACK LinkStaticProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_SETCURSOR:
        SetCursor(LoadCursor(nullptr, IDC_HAND));
        return TRUE;
    case WM_MOUSEMOVE:
        if (!g_LinkHover)
        {
            g_LinkHover = true;
            InvalidateRect(hWnd, nullptr, TRUE);
            TRACKMOUSEEVENT tme{ sizeof(TRACKMOUSEEVENT), TME_LEAVE, hWnd, 0 };
            TrackMouseEvent(&tme);
        }
        break;
    case WM_MOUSELEAVE:
        g_LinkHover = false;
        InvalidateRect(hWnd, nullptr, TRUE);
        break;
    case WM_LBUTTONUP:
        ShellExecuteW(nullptr, L"open", L"https://github.com/neptotech", nullptr, nullptr, SW_SHOWNORMAL);
        return 0;
    }
    return CallWindowProc(g_OldLinkProc, hWnd, msg, wParam, lParam);
}

int APIENTRY wWinMain(_In_ HINSTANCE hInstance,
                     _In_opt_ HINSTANCE hPrevInstance,
                     _In_ LPWSTR    lpCmdLine,
                     _In_ int       nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    // Initialize COM for Explorer detection (STA is fine for UI thread)
    CoInitialize(nullptr);

    LoadStringW(hInstance, IDS_APP_TITLE, szTitle, MAX_LOADSTRING);
    LoadStringW(hInstance, IDC_BETTERADVANCEDPASTE, szWindowClass, MAX_LOADSTRING);
    MyRegisterClass(hInstance);

    if (!InitInstance (hInstance, SW_HIDE))
    {
        CoUninitialize();
        return FALSE;
    }

    EnsureRunAtStartup();

    InstallKeyboardHook(hInstance, g_hMainWnd);

    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_BETTERADVANCEDPASTE));

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        if (!TranslateAccelerator(msg.hwnd, hAccelTable, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    UninstallKeyboardHook();
    CoUninitialize();

    return (int) msg.wParam;
}

ATOM MyRegisterClass(HINSTANCE hInstance)
{
    WNDCLASSEXW wcex;
    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style          = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc    = WndProc;
    wcex.cbClsExtra     = 0;
    wcex.cbWndExtra     = 0;
    wcex.hInstance      = hInstance;
    wcex.hIcon          = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_BETTERADVANCEDPASTE));
    wcex.hCursor        = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground  = (HBRUSH)(COLOR_WINDOW+1);
    wcex.lpszMenuName   = nullptr; // no menu for hidden window
    wcex.lpszClassName  = szWindowClass;
    wcex.hIconSm        = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));
    return RegisterClassExW(&wcex);
}

BOOL InitInstance(HINSTANCE hInstance, int nCmdShow)
{
   hInst = hInstance; 
   g_hMainWnd = CreateWindowW(szWindowClass, szTitle, WS_OVERLAPPEDWINDOW,
      CW_USEDEFAULT, 0, CW_USEDEFAULT, 0, nullptr, nullptr, hInstance, nullptr);

   if (!g_hMainWnd)
   {
      return FALSE;
   }

   // Hide window
   ShowWindow(g_hMainWnd, SW_HIDE);
   UpdateWindow(g_hMainWnd);

   // Add tray icon
   HICON hIcon = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_SMALL));
   CreateTrayIcon(g_hMainWnd, hIcon);

   return TRUE;
}

static void EnsureRunAtStartup()
{
    // Write registry Run key for current user
    HKEY hKey;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS)
    {
        wchar_t path[MAX_PATH];
        GetModuleFileNameW(nullptr, path, MAX_PATH);
        RegSetValueExW(hKey, L"BetterAdvancedPaste", 0, REG_SZ, (BYTE*)path, (DWORD)((wcslen(path)+1)*sizeof(wchar_t)));
        RegCloseKey(hKey);
    }
}

// Normalize path to avoid single backslashes by doubling them
static std::wstring EscapeBackslashes(const std::wstring& in)
{
    std::wstring out;
    out.reserve(in.size()*2);
    for (wchar_t c : in)
    {
        if (c == L'\\') out += L"\\\\"; else out += c;
    }
    return out;
}

static void LaunchBetterAdvancedPasteCLI(const std::wstring& folderPath)
{
    // Determine CLI exe path in the same directory as current exe
    wchar_t selfPath[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, selfPath, MAX_PATH);

    std::wstring dir(selfPath);
    size_t pos = dir.find_last_of(L"/\\");
    if (pos != std::wstring::npos)
        dir = dir.substr(0, pos + 1);
    else
        dir += L"\\";

    std::wstring cliPath = dir + L"BetterAdvancedPasteCLI.exe";

    // Build command line: "BetterAdvancedPasteCLI.exe" "escapedPath"
    std::wstring escaped = EscapeBackslashes(folderPath);
    std::wstring cmdLine = L"\"" + cliPath + L"\" \"" + escaped + L"\"";

    STARTUPINFOW si{}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};

    // CreateProcess requires mutable buffer for command line
    std::wstring mutableCmd = cmdLine;
    BOOL ok = CreateProcessW(
        nullptr, // application from command line
        &mutableCmd[0],
        nullptr,
        nullptr,
        FALSE,
        CREATE_NO_WINDOW,
        nullptr,
        nullptr,
        &si,
        &pi);

    if (ok)
    {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    }
}

static void OpenConfigFile()
{
    // Open conf.json located next to the running EXE
    wchar_t selfPath[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, selfPath, MAX_PATH);

    std::wstring dir(selfPath);
    size_t pos = dir.find_last_of(L"/\\");
    if (pos != std::wstring::npos)
        dir = dir.substr(0, pos + 1);
    else
        dir += L"\\";

    std::wstring cfg = dir + L"conf.json";
    ShellExecuteW(nullptr, L"open", cfg.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_CREATE:
        break;
    case WM_APP_HOTKEY_TRIGGER:
    {
        std::wstring folder = GetActiveExplorerFolder();
        if (!folder.empty())
        {
            LaunchBetterAdvancedPasteCLI(folder);
        }
    }
    break;
    case WM_APP_TRAYICON:
    {
        if (lParam == WM_RBUTTONUP || lParam == WM_CONTEXTMENU) {
            ShowTrayMenu(hWnd);
        } else if (lParam == WM_LBUTTONDBLCLK) {
            DialogBox(hInst, MAKEINTRESOURCE(IDD_ABOUTBOX), hWnd, About);
        }
    }
    break;
    case WM_COMMAND:
    {
        switch(LOWORD(wParam)) {
            case ID_TRAY_OPEN_CONFIG:
                OpenConfigFile();
                break;
            case ID_TRAY_EXIT:
            case IDM_EXIT:
                DestroyWindow(hWnd);
                break;
            case ID_TRAY_ABOUT:
            case IDM_ABOUT:
                DialogBox(hInst, MAKEINTRESOURCE(IDD_ABOUTBOX), hWnd, About);
                break;
            default:
                return DefWindowProc(hWnd, message, wParam, lParam);
        }
    }
    break;
    case WM_DESTROY:
        RemoveTrayIcon(hWnd);
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

INT_PTR CALLBACK About(HWND hDlg, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_INITDIALOG:
    {
        // Make the link underlined like a hyperlink and subclass for cursor/hover
        g_hLink = GetDlgItem(hDlg, IDC_MADEBY_LINK);
        if (g_hLink)
        {
            HFONT hFont = (HFONT)SendMessage(g_hLink, WM_GETFONT, 0, 0);
            LOGFONTW lf{};
            if (hFont && GetObjectW(hFont, sizeof(lf), &lf) == sizeof(lf))
            {
                lf.lfUnderline = TRUE;
                g_LinkFont = CreateFontIndirectW(&lf);
                if (g_LinkFont)
                    SendMessage(g_hLink, WM_SETFONT, (WPARAM)g_LinkFont, TRUE);
            }
            g_OldLinkProc = (WNDPROC)SetWindowLongPtr(g_hLink, GWLP_WNDPROC, (LONG_PTR)LinkStaticProc);
        }
        return (INT_PTR)TRUE;
    }
    case WM_CTLCOLORSTATIC:
    {
        if ((HWND)lParam == g_hLink)
        {
            HDC hdc = (HDC)wParam;
            // Dim color on hover
            COLORREF color = g_LinkHover ? RGB(0, 0, 180) : RGB(0, 0, 255);
            SetTextColor(hdc, color);
            SetBkMode(hdc, TRANSPARENT);
            return (INT_PTR)GetStockObject(HOLLOW_BRUSH);
        }
        break;
    }
    case WM_COMMAND:
        if (LOWORD(wParam) == IDOK || LOWORD(wParam) == IDCANCEL)
        {
            EndDialog(hDlg, LOWORD(wParam));
            return (INT_PTR)TRUE;
        }
        break;
    case WM_DESTROY:
        if (g_LinkFont)
        {
            DeleteObject(g_LinkFont);
            g_LinkFont = nullptr;
        }
        if (g_hLink && g_OldLinkProc)
        {
            SetWindowLongPtr(g_hLink, GWLP_WNDPROC, (LONG_PTR)g_OldLinkProc);
            g_OldLinkProc = nullptr;
        }
        g_hLink = nullptr;
        g_LinkHover = false;
        break;
    }
    return (INT_PTR)FALSE;
}
