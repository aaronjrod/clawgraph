from clawgraph.bag.node import clawnode
from clawgraph.core.models import ClawOutput, Signal
from clawgraph.orchestrator.graph import ClawBag


class TestInjectionSecurity:
    """F-REQ-20: Security workflow for Injection Testing."""

    def test_injection_testing_workflow(self, mock_gemini):
        bag = ClawBag(name="security_bag")

        @clawnode(id="secure_node", description="I am secure.", bag="security_bag")
        def secure_node(state: dict) -> ClawOutput:
            # Check for a specific 'injected' input to simulate adversarial testing
            injected_input = state.get("injected_payload")
            if injected_input == "DROP TABLE users;":
                return ClawOutput(
                    signal=Signal.FAILED,
                    node_id="secure_node",
                    orchestrator_summary="Injection attempt blocked!",
                )
            return ClawOutput(
                signal=Signal.DONE,
                node_id="secure_node",
                orchestrator_summary="Healthy execution.",
                result_uri="uri://secure_result.json",
            )

        bag.manager.register_node(secure_node)

        # 1. Start a normal job
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "secure_node"}, text="Normal run.")
        mock_gemini.add_expected_call("complete", {"final_summary": "Done."}, text="Finish.")

        result = bag.start_job(objective="Normal job.")
        assert result.get("current_output", {}).get("orchestrator_summary") == "Done."

        # 2. Simulate the Injection Testing workflow:
        # The Super-Orchestrator re-runs the node with a mutated input.
        # We verify the node correctly handles the injection.
        mock_gemini.add_expected_call("dispatch_node", {"node_id": "secure_node"}, text="Injected run.")
        mock_gemini.add_expected_call("escalate", {"reason": "Injection blocked.", "failure_class": "GUARDRAIL_VIOLATION"}, text="Thinking: Security test passed, injection was blocked.")

        # Re-starting or continuing with injected payload
        result_injected = bag.start_job(
            objective="Security probe.",
            inputs={"injected_payload": "DROP TABLE users;"}
        )

        # Verify the node failed as expected under injection
        # Note: In our current orchestrator, we expect this to trigger a failure signal.
        assert "pending_escalation" in result_injected
