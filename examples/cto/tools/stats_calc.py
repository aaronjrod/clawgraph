import math
from typing import Any

class StatsCalc:
    def calculate_variance(self, data: list[float]) -> dict[str, Any]:
        """Calculate statistical variance with a 2% fence logic.
        
        Args:
            data: A list of numeric data points to analyze.
        """
        if not data:
            return {"error": "Empty data"}
            
        n = len(data)
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = math.sqrt(variance)
        
        # 2% Fence logic: Is the variance within 2% of the mean?
        status = "PASSED" if (std_dev / mean) < 0.02 else "FAILED"
        
        print(f"🔢 [StatsCalc] Variance: {variance:.4f} (Status: {status})")
        return {
            "mean": round(mean, 4),
            "variance": round(variance, 4),
            "std_dev": round(std_dev, 4),
            "status": status
        }

    def align_pk_metrics(self, baseline_metrics: dict[str, float], target_metrics: dict[str, float]) -> dict[str, Any]:
        """Compare Pharmacokinetics across drug generations using Euclidean distance."""
        print(f"🔢 [StatsCalc] Aligning PK metrics...")
        
        keys = set(baseline_metrics.keys()) & set(target_metrics.keys())
        if not keys:
            return {"error": "No overlapping metrics found"}
            
        diff_sq = 0
        for k in keys:
            diff_sq += (baseline_metrics[k] - target_metrics[k])**2
            
        dist = math.sqrt(diff_sq)
        # Normalize score (arbitrary heuristic)
        alignment_score = max(0, 1 - (dist / sum(baseline_metrics.values())))
        
        return {
            "alignment_score": round(alignment_score, 4),
            "recommendation": "Safety carry-over accepted." if alignment_score > 0.95 else "In-depth review required."
        }
