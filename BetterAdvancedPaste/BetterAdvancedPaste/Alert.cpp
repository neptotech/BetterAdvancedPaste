#include "framework.h"
#include "Alert.h"

void ShowHotkeyAlert(const std::wstring& explorerPath) {
    std::wstring msg = L"Win + Shift + V detected";
    if(!explorerPath.empty()) {
        msg += L"\nFolder: " + explorerPath;
    }
    MessageBoxW(nullptr, msg.c_str(), L"BetterAdvancedPaste", MB_OK | MB_ICONINFORMATION | MB_TOPMOST);
}
