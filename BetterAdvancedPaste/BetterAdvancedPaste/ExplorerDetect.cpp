#include "framework.h"
#include "ExplorerDetect.h"
#include <shlwapi.h>
#include <shlobj.h>
#include <exdisp.h>
#include <shlguid.h>
#include <shobjidl.h>
#include <oleacc.h>
#pragma comment(lib, "oleacc.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "shlwapi.lib")

// Try to resolve the real filesystem path of the foreground Explorer window
static std::wstring ResolvePathFromExplorerHWND(HWND hwndExplorer)
{
    std::wstring result;
    IShellWindows* pShellWindows = nullptr;
    if (FAILED(CoCreateInstance(CLSID_ShellWindows, nullptr, CLSCTX_ALL, IID_PPV_ARGS(&pShellWindows))))
        return result;

    long count = 0;
    if (FAILED(pShellWindows->get_Count(&count))) {
        pShellWindows->Release();
        return result;
    }

    for (long i = 0; i < count; ++i)
    {
        VARIANT vtIndex; VariantInit(&vtIndex); vtIndex.vt = VT_I4; vtIndex.lVal = i;
        VARIANT vtEmpty; VariantInit(&vtEmpty);
        IDispatch* pDisp = nullptr;
        if (FAILED(pShellWindows->Item(vtIndex, &pDisp)) || !pDisp) {
            VariantClear(&vtIndex); VariantClear(&vtEmpty); continue;
        }

        IWebBrowserApp* pWBA = nullptr;
        if (FAILED(pDisp->QueryInterface(IID_PPV_ARGS(&pWBA))) || !pWBA) {
            pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); continue;
        }

        SHANDLE_PTR handle = 0;
        if (FAILED(pWBA->get_HWND(reinterpret_cast<LONG_PTR*>(&handle)))) {
            pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); continue;
        }

        HWND hwndWBA = (HWND)handle;
        if (hwndWBA != hwndExplorer) {
            pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); continue;
        }

        IServiceProvider* pSP = nullptr;
        if (FAILED(pWBA->QueryInterface(IID_PPV_ARGS(&pSP))) || !pSP) {
            pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); break;
        }

        IShellBrowser* pBrowser = nullptr;
        if (FAILED(pSP->QueryService(SID_STopLevelBrowser, IID_PPV_ARGS(&pBrowser))) || !pBrowser) {
            pSP->Release(); pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); break;
        }

        IShellView* pView = nullptr;
        if (FAILED(pBrowser->QueryActiveShellView(&pView)) || !pView) {
            pBrowser->Release(); pSP->Release(); pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); break;
        }

        IFolderView* pFolderView = nullptr;
        if (FAILED(pView->QueryInterface(IID_PPV_ARGS(&pFolderView))) || !pFolderView) {
            pView->Release(); pBrowser->Release(); pSP->Release(); pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); break;
        }

        IPersistFolder2* pPersist = nullptr;
        if (FAILED(pFolderView->GetFolder(IID_PPV_ARGS(&pPersist))) || !pPersist) {
            pFolderView->Release(); pView->Release(); pBrowser->Release(); pSP->Release(); pWBA->Release(); pDisp->Release();
            VariantClear(&vtIndex); VariantClear(&vtEmpty); break;
        }

        PIDLIST_ABSOLUTE pidl = nullptr;
        if (SUCCEEDED(pPersist->GetCurFolder(&pidl)) && pidl) {
            wchar_t path[MAX_PATH];
            if (SHGetPathFromIDListW(pidl, path)) {
                result = path;
            }
            CoTaskMemFree(pidl);
        }

        pPersist->Release();
        pFolderView->Release();
        pView->Release();
        pBrowser->Release();
        pSP->Release();
        pWBA->Release();
        pDisp->Release();
        VariantClear(&vtIndex); VariantClear(&vtEmpty);
        break; // done with foreground
    }

    pShellWindows->Release();
    return result;
}

// Fallback: window title when robust method fails
static std::wstring FallbackWindowTitle(HWND hwnd)
{
    wchar_t title[512] = {};
    GetWindowTextW(hwnd, title, 512);
    return title;
}

// Public API
std::wstring GetActiveExplorerFolder() {
    HWND fg = GetForegroundWindow();
    if(!fg) return L"";
    wchar_t cls[64] = {};
    if(GetClassNameW(fg, cls, 64) == 0) return L"";
    if(wcscmp(cls, L"CabinetWClass") != 0 && wcscmp(cls, L"ExploreWClass") != 0) {
        return L""; // not explorer
    }

    std::wstring resolved = ResolvePathFromExplorerHWND(fg);
    if(!resolved.empty()) return resolved;

    return FallbackWindowTitle(fg);
}
