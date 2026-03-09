import logging

from clawgraph import ClawBag, clawnode
from clawgraph.bag.patterns import AggregatorBuilder, CheckResult, VerificationNode
from clawgraph.core.models import AggregatorOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Specialists ---

def analyze_impurity(state):
    vn = VerificationNode("impurity_specialist")
    # Simulate data check
    checks = [CheckResult(name="Impurity A", passed=True)]
    return vn.evaluate(checks, "uri://cmc/impurity-report.pdf")

def analyze_stability(state):
    vn = VerificationNode("stability_specialist")
    # Simulate data check
    checks = [CheckResult(name="Shelf Life", passed=True)]
    return vn.evaluate(checks, "uri://cmc/stability-report.pdf")

# --- Aggregator ---

@clawnode(
    id="cmc_quality_gate",
    description="Aggregates parallel impurity and stability checks.",
    bag="cmc_regulatory"
)
def cmc_quality_gate(state: dict[str, Any]) -> AggregatorOutput:
    builder = AggregatorBuilder(aggregator_id="cmc_quality_gate", partial_commit_policy="eager")

    # Fan-out
    builder.add_branch("impurity", "impurity_specialist", analyze_impurity)
    builder.add_branch("stability", "stability_specialist", analyze_stability)

    # Fan-in
    result = builder.run(state)
    return result.output

def run_simulation():
    bag = ClawBag("cmc_regulatory")
    bag.manager.register_node(cmc_quality_gate)

    print("\n[SUPER-ORCHESTRATOR] Initializing Parallel CMC Review...")
    state = bag.start_job(objective="Finalize CMC technical validation for IND submission.")

    print("\nAggregation Results:")
    output = state.get("current_output", {})
    print(f"  Signal: {output.get('signal')}")
    print(f"  Summary: {output.get('orchestrator_summary')}")

    for branch in output.get("branch_breakdown", []):
        print(f"    - Branch {branch['branch_id']} ({branch['node_id']}): {branch['signal']}")

if __name__ == "__main__":
    run_simulation()
