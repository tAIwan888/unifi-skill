from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PublicArchitectureAcceptance(unittest.TestCase):
    def test_core_modules_cite_official_and_disclose_limited_evidence(self):
        modules=["modules/M01-platform.md","modules/M09-backup-security.md"]
        for name in modules:
            s=(ROOT/name).read_text(encoding="utf-8")
            with self.subTest(module=name):
                self.assertIn("https://help.ui.com/hc/en-us/articles/",s)
                self.assertIn("DOC_REVIEWED",s)
                self.assertIn("## 核心概念",s)
                self.assertIn("## 官方建議做法",s)
                self.assertIn("## UI 操作路徑",s)
                self.assertIn("## CLI / API 替代方法",s)
                self.assertIn("## 風險與注意事項",s)
                self.assertIn("## 驗證方式",s)
                self.assertIn("## 故障排除流程",s)
                self.assertIn("## 官方文件連結",s)
    def test_cross_product_unsafe_assumptions_are_rejected(self):
        control=(ROOT/"modules/M01-platform.md").read_text(encoding="utf-8")
        backup=(ROOT/"modules/M09-backup-security.md").read_text(encoding="utf-8")
        self.assertIn("外部 UniFi OS Server",control)
        self.assertIn("Protect/Access/Talk/Connect",control)
        self.assertIn("Docker",control)
        self.assertIn("Site Manager",control)
        self.assertIn("Local",control)
        self.assertIn("Network-only",backup)
        self.assertIn(".unf",backup)
        self.assertIn("Managed by Another Console",backup)
        self.assertIn("錄影不可直接跨 Console 轉移",backup)
        self.assertIn("UniFi OS 3.1",backup)
    def test_public_compatibility_matrix_is_present(self):
        s=(ROOT/"docs/control-plane-and-migration-matrix.md").read_text(encoding="utf-8")
        self.assertIn("DOC_REVIEWED",s)
        self.assertIn("UXG",s)
        self.assertIn("備份與資料移轉",s)
        self.assertIn("不主動蒐集任何私人設備清單",s)
if __name__=="__main__":
    unittest.main()
