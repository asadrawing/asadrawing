# ai_analyzer.py
import json
import openai

class DrawingAIAnalyzer:
    def __init__(self, api_key, lang="Swedish", *args, **kwargs):
        self.api_key = api_key
        self.lang = lang

    def analyze_drawing_with_ai(self, drawing_text, metadata_str="", parameters=None, *args, **kwargs):
        if not self.api_key or self.api_key.strip() == "":
            return [{"rule_id": "AI-INFO", "severity": "Information", "description": "OpenAI API-nyckel saknas. AI-analysen har hoppats över.", "remediation": "Ange en giltig API-nyckel i sidofältet."}]
        
        if parameters is None:
            parameters = {}

        calc_weight = parameters.get("calc_weight", 0.14)
        calc_volume = parameters.get("calc_volume", 50.0)
        mat_name = parameters.get("mat_name", "Aluminium (Al6061-T6)")

        prompt = f"""
        You are a strict expert in manufacturing, CNC, DFM, and ISO standards.
        Analyze the drawing text and metadata. Provide descriptions and remediation suggestions in {self.lang}.
        Metadata: {metadata_str}
        Weight = {calc_weight:.2f} kg, Volume = {calc_volume:.1f} cm3, Material = {mat_name}
        
        Drawing Text:
        {drawing_text}

        Return the result strictly as a valid JSON list with objects containing keys:
        - "rule_id": string (e.g. "RULE-DFM-01")
        - "severity": "Critical", "Warning", "Information" or "Approved"
        - "description": Detailed description of the issue in {self.lang}.
        - "remediation": Concrete, professional engineering text or action suggestion to fix this issue in {self.lang}.
        """

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You review manufacturing drawings and return strict JSON with remediation advice in {self.lang}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            content = content.strip()

            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]

            issues = json.loads(content)
            return issues if isinstance(issues, list) else []
        except Exception as e:
            return [{"rule_id": "AI-ERROR", "severity": "Warning", "description": f"AI-analysfel: {str(e)}", "remediation": "Kontrollera API-nyckel och nätverksanslutning."}]