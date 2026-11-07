import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

from agentprobe.llm.wrapper import MockProvider
from agentprobe.schemas import ToolCall
from agentprobe.targets.banking import BankingAgent
from agentprobe.targets.email import EmailAgent
from agentprobe.targets.web import WebResearchAgent


# --- Test Web Server Fixture ---
class MockHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Mock Page Content</body></html>")


@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("localhost", 0), MockHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://localhost:{port}"
    server.shutdown()


# --- Agent Utility Tests ---
def test_email_agent_utility():
    provider = MockProvider(
        mock_responses=[
            (
                "Reading email",
                [
                    ToolCall(
                        call_id="1", name="read_email", arguments={"msg_id": "msg_1"}
                    )
                ],
            ),
            (
                "Sending reply",
                [
                    ToolCall(
                        call_id="2",
                        name="send_email",
                        arguments={
                            "recipient": "boss@company.fake",
                            "body": "Will do!",
                        },
                    )
                ],
            ),
            ("Done", []),
        ]
    )

    agent = EmailAgent(llm=provider)
    trace = agent.run(task_id="t1", task_desc="Reply to boss")

    assert len(trace.steps) == 3
    assert agent.outbox[0]["to"] == "boss@company.fake"
    assert "Will do!" in agent.outbox[0]["body"]
    assert "Done" in trace.final_answer


def test_web_agent_utility(mock_server):
    provider = MockProvider(
        mock_responses=[
            (
                "Fetching",
                [
                    ToolCall(
                        call_id="1", name="fetch_page", arguments={"url": mock_server}
                    )
                ],
            ),
            ("Summary", []),
        ]
    )

    agent = WebResearchAgent(llm=provider)
    trace = agent.run(task_id="t2", task_desc="Summarize page")

    assert len(trace.steps) == 2
    assert (
        trace.steps[0].tool_results[0].result
        == "<html><body>Mock Page Content</body></html>"
    )


def test_banking_agent_utility():
    provider = MockProvider(
        mock_responses=[
            (
                "Transferring",
                [
                    ToolCall(
                        call_id="1",
                        name="transfer",
                        arguments={
                            "from_acc": "checking",
                            "to_acc": "savings",
                            "amount": 1000.0,
                        },
                    )
                ],
            ),
            ("Done", []),
        ]
    )

    agent = BankingAgent(llm=provider)
    agent.run(task_id="t3", task_desc="Move 1000 to savings")

    assert agent.accounts["checking"] == 4000.0
    assert agent.accounts["savings"] == 16000.0
