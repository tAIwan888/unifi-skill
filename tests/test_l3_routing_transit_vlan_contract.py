"""Document-only guard for official L3 switch transit VLAN restrictions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Layer3TransitVlanContract(unittest.TestCase):
    def test_transit_vlan_is_fixed_while_transit_subnet_is_configurable(self):
        doc = (ROOT / "modules" / "M02-networks.md").read_text(encoding="utf-8")
        route_line = next(line for line in doc.splitlines()
                          if line.startswith("6. Layer 3 Switch Routing"))
        self.assertIn("VLAN ID 4040（不可變更）", route_line)
        self.assertIn("`10.255.253.0/24` 是**可調整的預設子網**", route_line)
        self.assertIn("Tagged VLAN 4040", route_line)
        self.assertIn("Static Routes", route_line)
        self.assertIn("https://help.ui.com/hc/en-us/articles/360042281174-Layer-3-Routing", doc)

if __name__ == "__main__":
    unittest.main()
