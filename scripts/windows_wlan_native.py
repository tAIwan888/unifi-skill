#!/usr/bin/env python3
"""Windows native WLAN read-only evidence: associated BSSID's BSS frequency + RSSI.

Only exports allowlisted numeric telemetry. SSID/BSSID/MAC/profile/interface ID never
leave process memory. No scan, connection change, elevation, or network request.
Win32 definitions follow the Microsoft wlanapi.h Native Wifi ABI.
"""
import ctypes
import sys
from ctypes import wintypes

U8 = ctypes.c_ubyte
U16 = ctypes.c_uint16
U32 = ctypes.c_uint32
I32 = ctypes.c_int32
U64 = ctypes.c_uint64

class GUID(ctypes.Structure):
    _fields_ = [("Data1", U32), ("Data2", U16), ("Data3", U16), ("Data4", U8 * 8)]

class DOT11_SSID(ctypes.Structure):
    _fields_ = [("length", U32), ("value", U8 * 32)]

class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [("guid", GUID), ("description", wintypes.WCHAR * 256), ("state", U32)]

class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [("count", U32), ("index", U32), ("items", WLAN_INTERFACE_INFO * 1)]

class WLAN_ASSOCIATION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("ssid", DOT11_SSID), ("bss_type", U32), ("bssid", U8 * 6),
        ("phy_type", U32), ("phy_index", U32), ("signal_quality", U32),
        ("rx_rate_kbps", U32), ("tx_rate_kbps", U32),
    ]

class WLAN_SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("security_enabled", wintypes.BOOL), ("one_x_enabled", wintypes.BOOL),
        ("auth_algorithm", U32), ("cipher_algorithm", U32),
    ]

class WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("state", U32), ("mode", U32), ("profile", wintypes.WCHAR * 256),
        ("association", WLAN_ASSOCIATION_ATTRIBUTES),
        ("security", WLAN_SECURITY_ATTRIBUTES),
    ]

class WLAN_RATE_SET(ctypes.Structure):
    _fields_ = [("length", U32), ("rates", U16 * 126)]

class WLAN_BSS_ENTRY(ctypes.Structure):
    _fields_ = [
        ("ssid", DOT11_SSID), ("phy_id", U32), ("bssid", U8 * 6),
        ("bss_type", U32), ("phy_type", U32), ("rssi_dbm", I32),
        ("quality_pct", U32), ("in_reg_domain", U8), ("beacon_period", U16),
        ("timestamp", U64), ("host_timestamp", U64), ("capabilities", U16),
        ("center_frequency_khz", U32), ("rates", WLAN_RATE_SET),
        ("ie_offset", U32), ("ie_size", U32),
    ]

class WLAN_BSS_LIST(ctypes.Structure):
    _fields_ = [("total_size", U32), ("count", U32), ("items", WLAN_BSS_ENTRY * 1)]

STATUS = {"NOT_WINDOWS", "NOT_CONNECTED", "LOCATION_PERMISSION_REQUIRED",
          "NATIVE_API_UNAVAILABLE", "BSS_NOT_MATCHED", "OBSERVED",
          "AMBIGUOUS_MULTIPLE_CONNECTIONS"}


def band_from_frequency_mhz(frequency):
    """True band from MHz, not channel number or PHY/adapter capability."""
    if not isinstance(frequency, (int, float)) or isinstance(frequency, bool):
        return None
    if 2400 <= frequency <= 2500:
        return 2.4
    if 4900 <= frequency < 5925:
        return 5.0
    if 5925 <= frequency <= 7125:
        return 6.0
    return None


def sanitized_sample(center_frequency_khz, rssi_dbm, quality, rx_kbps, tx_kbps):
    """Never infer RSSI from signal %, and never call link rates throughput."""
    frequency_mhz = center_frequency_khz / 1000.0
    band = band_from_frequency_mhz(frequency_mhz)
    if band is None or not (-110 <= rssi_dbm <= -15) or not (0 <= quality <= 100):
        return None
    return {
        "status": "OBSERVED", "source": "WINDOWS_WLAN_API_ASSOCIATED_BSS",
        "band_ghz": band, "bss_center_frequency_mhz": round(frequency_mhz, 3),
        "rssi_dbm": int(rssi_dbm), "signal_quality_percent": int(quality),
        "rx_phy_mbps": round(rx_kbps / 1000, 2) if 0 < rx_kbps <= 100000000 else None,
        "tx_phy_mbps": round(tx_kbps / 1000, 2) if 0 < tx_kbps <= 100000000 else None,
        "not_throughput": True,
    }


def sample():
    if sys.platform != "win32":
        return {"status": "NOT_WINDOWS"}
    try:
        dll = ctypes.WinDLL("wlanapi.dll")
        dll.WlanOpenHandle.argtypes = [U32, ctypes.c_void_p, ctypes.POINTER(U32), ctypes.POINTER(ctypes.c_void_p)]
        dll.WlanOpenHandle.restype = U32
        dll.WlanEnumInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        dll.WlanEnumInterfaces.restype = U32
        dll.WlanQueryInterface.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID), U32, ctypes.c_void_p,
                                          ctypes.POINTER(U32), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(U32)]
        dll.WlanQueryInterface.restype = U32
        dll.WlanGetNetworkBssList.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID),
             ctypes.POINTER(DOT11_SSID), U32, wintypes.BOOL, ctypes.c_void_p,
             ctypes.POINTER(ctypes.c_void_p)]
        dll.WlanGetNetworkBssList.restype = U32
        dll.WlanFreeMemory.argtypes = [ctypes.c_void_p]
        dll.WlanFreeMemory.restype = None
        dll.WlanCloseHandle.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        dll.WlanCloseHandle.restype = U32
    except (OSError, AttributeError):
        return {"status": "NATIVE_API_UNAVAILABLE"}
    handle, negotiated = ctypes.c_void_p(), U32()
    code = dll.WlanOpenHandle(2, None, ctypes.byref(negotiated), ctypes.byref(handle))
    if code:
        return {"status": "LOCATION_PERMISSION_REQUIRED" if code == 5 else "NATIVE_API_UNAVAILABLE"}
    iface_ptr = ctypes.c_void_p()
    try:
        code = dll.WlanEnumInterfaces(handle, None, ctypes.byref(iface_ptr))
        if code:
            return {"status": "LOCATION_PERMISSION_REQUIRED" if code == 5 else "NATIVE_API_UNAVAILABLE"}
        try:
            header = ctypes.cast(iface_ptr, ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)).contents
            # Reject unexpected buffers / multi-WiFi without guessing which one is tested.
            if header.count > 16:
                return {"status": "NATIVE_API_UNAVAILABLE"}
            connected = []
            start = iface_ptr.value + WLAN_INTERFACE_INFO_LIST.items.offset
            step = ctypes.sizeof(WLAN_INTERFACE_INFO)
            for i in range(header.count):
                item = ctypes.cast(start + i * step, ctypes.POINTER(WLAN_INTERFACE_INFO)).contents
                if item.state == 1:  # wlan_interface_state_connected
                    connected.append(item.guid)
        finally:
            dll.WlanFreeMemory(iface_ptr)
        if not connected:
            return {"status": "NOT_CONNECTED"}
        if len(connected) != 1:
            return {"status": "AMBIGUOUS_MULTIPLE_CONNECTIONS"}
        guid = connected[0]
        size, opcode_type, connection_ptr = U32(), U32(), ctypes.c_void_p()
        # wlan_intf_opcode_current_connection = 7
        code = dll.WlanQueryInterface(handle, ctypes.byref(guid), 7, None,
                                      ctypes.byref(size), ctypes.byref(connection_ptr),
                                      ctypes.byref(opcode_type))
        if code:
            return {"status": "LOCATION_PERMISSION_REQUIRED" if code == 5 else "NATIVE_API_UNAVAILABLE"}
        try:
            if size.value < ctypes.sizeof(WLAN_CONNECTION_ATTRIBUTES):
                return {"status": "NATIVE_API_UNAVAILABLE"}
            conn = ctypes.cast(connection_ptr, ctypes.POINTER(WLAN_CONNECTION_ATTRIBUTES)).contents
            if conn.state != 1:
                return {"status": "NOT_CONNECTED"}
            assoc = conn.association
            target_bssid = bytes(assoc.bssid)
            target_ssid = bytes(assoc.ssid.value[:min(assoc.ssid.length, 32)])
            bss_type = assoc.bss_type
            if assoc.ssid.length > 32 or bss_type not in (1, 2):
                return {"status": "NATIVE_API_UNAVAILABLE"}
            assoc_quality = int(assoc.signal_quality)
            rx, tx = int(assoc.rx_rate_kbps), int(assoc.tx_rate_kbps)
            security = bool(conn.security.security_enabled)
            ssid = assoc.ssid
        finally:
            dll.WlanFreeMemory(connection_ptr)
        bss_ptr = ctypes.c_void_p()
        code = dll.WlanGetNetworkBssList(handle, ctypes.byref(guid),
                                         ctypes.byref(ssid), bss_type, security,
                                         None, ctypes.byref(bss_ptr))
        if code:
            return {"status": "LOCATION_PERMISSION_REQUIRED" if code == 5 else "BSS_NOT_MATCHED"}
        try:
            header = ctypes.cast(bss_ptr, ctypes.POINTER(WLAN_BSS_LIST)).contents
            if header.count > 1024 or header.total_size > 4 * 1024 * 1024:
                return {"status": "NATIVE_API_UNAVAILABLE"}
            start = bss_ptr.value + WLAN_BSS_LIST.items.offset
            step = ctypes.sizeof(WLAN_BSS_ENTRY)
            if header.total_size < WLAN_BSS_LIST.items.offset + header.count * step:
                return {"status": "NATIVE_API_UNAVAILABLE"}
            matches = []
            for i in range(header.count):
                bss = ctypes.cast(start + i * step, ctypes.POINTER(WLAN_BSS_ENTRY)).contents
                if bytes(bss.bssid) != target_bssid or bss.ssid.length > 32:
                    continue
                if bytes(bss.ssid.value[:bss.ssid.length]) != target_ssid:
                    continue
                sample_data = sanitized_sample(bss.center_frequency_khz, bss.rssi_dbm,
                                               assoc_quality, rx, tx)
                if sample_data is not None:
                    matches.append(sample_data)
            return matches[0] if len(matches) == 1 else {"status": "BSS_NOT_MATCHED"}
        finally:
            dll.WlanFreeMemory(bss_ptr)
    finally:
        dll.WlanCloseHandle(handle, None)


if __name__ == "__main__":
    import json
    print(json.dumps(sample(), ensure_ascii=False))
