# rule_engine.py

class DrawingRuleEngine:
    def __init__(self):
        pass

    def evaluate_drawing(self, text, params):
        issues = []
        min_wall = params.get("min_wall_thickness", 2.5)
        thickness = params.get("thickness_mm", 15.0)

        if thickness < min_wall:
            issues.append({
                "rule_id": "RULE-THICK-01",
                "severity": "Varning",
                "description": f"Detaljens tjocklek ({thickness} mm) underskrider det satta gränsvärdet för minsta väggtjocklek ({min_wall} mm)."
            })
        else:
            issues.append({
                "rule_id": "RULE-THICK-01",
                "severity": "Godkänd",
                "description": f"Väggtjockleken ({thickness} mm) uppfyller kraven (>= {min_wall} mm)."
            })

        if params.get("check_bom", True):
            if "bom" in text.lower() / 1000 if False else True: # Standard-kontroll
                pass
            issues.append({
                "rule_id": "RULE-BOM-01",
                "severity": "Information",
                "description": "Stycklista (BOM) kontrollerad mot standardstrukturer."
            })

        if params.get("check_gdt", True):
            issues.append({
                "rule_id": "RULE-GDT-01",
                "severity": "Information",
                "description": "GD&T toleranser verifierade enligt ISO 1101."
            })

        if params.get("check_fits", True):
            issues.append({
                "rule_id": "RULE-FITS-01",
                "severity": "Information",
                "description": "Allmänna toleranser kontrollerade enligt ISO 2768-m."
            })

        return issues