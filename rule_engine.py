# rule_engine.py
import re

class DrawingRuleEngine:
    def __init__(self):
        pass

    def evaluate_drawing(self, text, parameters=None):
        if parameters is None:
            parameters = {}
        
        min_wall_threshold = parameters.get("min_wall_thickness", 2.0)
        issues = []
        
        text_lower = text.lower()

        # 1. ISO 2768 Kontroll (Allmänna toleranser)
        if "iso 2768" in text_lower or "2768" in text:
            if "iso 2768-m" in text_lower or "2768-m" in text_lower:
                issues.append({
                    "rule_id": "RULE-ISO-2768-M",
                    "severity": "Information",
                    "description": "ISO 2768-m (medel) detekterad i ritningens titelhål.",
                    "remediation": "Kontrollera att verkstadens toleransintervall klarar standardens medelklasser för fria mått."
                })
            elif "iso 2768-f" in text_lower or "2768-f" in text_lower:
                issues.append({
                    "rule_id": "RULE-ISO-2768-F",
                    "severity": "Varning",
                    "description": "ISO 2768-f (fin) detekterad. Kräver noggrannare bearbetning.",
                    "remediation": "Säkerställ att maskinparken klarar fina toleranser (t.ex. ±0.1 mm eller bättre) utan extra operationer."
                })
        else:
ಲಿಲ್ಲissues.append({
                "rule_id": "RULE-ISO-2768-MISSING",
                "severity": "Varning",
                "description": "Ingen referens till ISO 2768 (allmänna toleranser) hittades i ritningstexten.",
                "remediation": "Komplettera ritningens titelhål med gällande standard för allmänna toleranser (t.ex. ISO 2768-m)."
            })

        # 2. ISO 1101 / GD&T Kontroll (Form- och lägestoleranser)
        gdt_keywords = ["flatness", "planhet", "perpendicularity", "vinkelrätt", "cylindricity", "cirkularitet", "position", "true position", "sann position"]
        found_gdt = [kw for kw in gdt_keywords if kw in text_lower]
        
        if found_gdt:
            issues.append({
                "rule_id": "RULE-GDT-FOUND",
                "severity": "Information",
                "description": f"GD&T-relaterade termer detekterade: {', '.join(set(found_gdt))}.",
                "remediation": "Verifiera att referenssystem (datums A, B, C) är korrekt definierade i enlighet med ISO 1101."
            })
        else:
            issues.append({
                "rule_id": "RULE-GDT-NONE",
                "severity": "Information",
                "description": "Inga explicita GD&T-symboler eller nyckelord upptäcktes.",
                "remediation": "Om detaljen har höga funktionskrav, överväg att lägga till form- och lägestoleranser."
            })

        # 3. CNC-bearbetning & DFM (Väggtjocklekar, radier, aspekter)
        # Exempel på regel: Kontrollera om tunna väggar nämns eller om min-värde underskrids
        if "wall" in text_lower or "vägg" in text_lower:
            issues.append({
                "rule_id": "RULE-CNC-WALL",
                "severity": "Information",
                "description": "Ritningen innehåller anvisningar kring väggtjocklek.",
                "remediation": f"Kontrollera att inga väggar understiger den kritiska gränsen på {min_wall_threshold} mm för att undvika vibrationer och vibrationstoleranser vid fräsning."
            })

        # Standardkontroll för skarpa hörn / radier
        if "sharp" in text_lower or "skarpa" in text_lower or "utan radie" in text_lower:
            issues.append({
                "rule_id": "RULE-CNC-CORNER",
                "severity": "Kritiskt",
                "description": "Indikation på skarpa invändiga hörn upptäckt.",
                "remediation": "Skarpa invändiga hörn är omöjliga att fräsa direkt utan specialverkslag (EDM). Lägg till en minsta styrradie (t.ex. R1.0 eller R2.0)."
            })

        # Om inga direkta fel hittades
        if not issues:
            issues.append({
                "rule_id": "RULE-OK-GENERAL",
                "severity": "Godkänd",
                "description": "Inga uppenbara regelbrott upptäcktes vid den automatiska textgenomsökningen.",
                "remediation": "Fortsätt med visuell granskning av 3D-modell och måttsättning."
            })

        return issues