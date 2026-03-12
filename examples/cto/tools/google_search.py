class GoogleSearch:
    def __init__(self):
        self.kb = {
            "ich e6": "ICH E6 (R2) provides Good Clinical Practice (GCP) guidelines for clinical trials...",
            "fda 356h instructions": "Form FDA 356h is used for New Drug Applications (NDAs)... Section 28 requires establishment info...",
            "nm5082 mechanism": "NM5082 is a selective IL-13 inhibitor targeting moderate-to-severe atopic dermatitis...",
            "atopic dermatitis benchmarks": "Standard EASI-75 response rates for IL-13 inhibitors range from 35% to 55% at Week 16...",
            "pharmacovigilance signal": "Signal detection in pharmacovigilance involves identifying new or changed safety information for a drug product...",
        }

    def search(self, query: str) -> str:
        """Perform a realistic simulated internet search using a regulatory knowledge base."""
        query_lower = query.lower()
        print(f"🔎 [GoogleSearch] Searching for: {query}")
        
        matches = []
        for key, text in self.kb.items():
            if key in query_lower:
                matches.append(text)
        
        if not matches:
            return f"No direct regulatory matches for '{query}'. General search indicates standard industry practices apply."
            
        return " | ".join(matches)
