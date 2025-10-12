#pragma once
#include <windows.h>
#include <shellapi.h>

bool CreateTrayIcon(HWND hWnd, HICON hIcon);
void RemoveTrayIcon(HWND hWnd);
void ShowTrayMenu(HWND hWnd);

#define ID_TRAY_EXIT         40001
#define ID_TRAY_ABOUT        40002
#define ID_TRAY_OPEN_CONFIG  40003
