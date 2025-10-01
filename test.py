import win32clipboard as cb
import win32con
import struct

def list_clipboard_formats():
    cb.OpenClipboard()
    try:
        formats = []
        fmt = 0
        while True:
            fmt = cb.EnumClipboardFormats(fmt)
            if fmt == 0:
                break
            try:
                name = cb.GetClipboardFormatName(fmt)
            except Exception:
                # Fallback to predefined format name if available
                standard_names = {
                    win32con.CF_TEXT: "CF_TEXT",
                    win32con.CF_UNICODETEXT: "CF_UNICODETEXT",
                    win32con.CF_BITMAP: "CF_BITMAP",
                    win32con.CF_DIB: "CF_DIB",
                    win32con.CF_DIBV5: "CF_DIBV5",
                    win32con.CF_HDROP: "CF_HDROP",
                    win32con.CF_LOCALE: "CF_LOCALE",
                    win32con.CF_WAVE: "CF_WAVE",
                    win32con.CF_TIFF: "CF_TIFF",
                }
                name = standard_names.get(fmt, f"Format#{fmt}")
            formats.append((fmt, name))
        return formats
    finally:
        cb.CloseClipboard()

def get_clipboard_data(fmt):
    cb.OpenClipboard()
    try:
        if cb.IsClipboardFormatAvailable(fmt):
            data = cb.GetClipboardData(fmt)
            return data
    except Exception as e:
        return f"<Error: {e}>"
    finally:
        cb.CloseClipboard()
    return None

if __name__ == "__main__":
    formats = list_clipboard_formats()
    print("📋 Clipboard contains formats:\n")
    for fmt, name in formats:
        print(f"- {name} ({fmt})")
        content = get_clipboard_data(fmt)
        if isinstance(content, bytes):
            # truncate long binary for display
            print(f"   Content (bytes): {content[:50]}{'...' if len(content) > 50 else ''}")
        elif isinstance(content, str):
            print(f"   Content (string): {content[:200]}{'...' if len(content) > 200 else ''}")
        elif isinstance(content, list):
            print(f"   Content (list): {content}")
        else:
            print(f"   Content (object): {type(content)} -> {content}")
