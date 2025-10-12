#pragma once
#include <windows.h>

bool InstallKeyboardHook(HINSTANCE hInst, HWND notifyHwnd);
void UninstallKeyboardHook();
