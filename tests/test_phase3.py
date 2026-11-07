from agentprobe.attacks.injector import InjectionEngine
from agentprobe.attacks.loader import load_seeds
from agentprobe.attacks.mutator import AttackMutator
from agentprobe.llm.wrapper import MockProvider
from agentprobe.schemas import Attack
from agentprobe.targets.email import EmailAgent


def test_loader(tmp_path):
    d = tmp_path / "seeds"
    d.mkdir()
    p = d / "test.yaml"
    p.write_text("""
- id: "test_seed"
  category: "obfuscation"
  severity: "high"
  target: "email"
  payload: "hello"
  placement: "email_body"
  success_criteria: "none"
    """)

    attacks = load_seeds(str(d))
    assert len(attacks) == 1
    assert attacks[0].id == "test_seed"


def test_mutator():
    # Mock returning 200 dummy variants
    mock_resp = "\n".join([f"VARIANT: hacked payload {i}" for i in range(200)])
    provider = MockProvider(mock_responses=[(mock_resp, [])])
    mutator = AttackMutator(llm=provider)

    seed = Attack(
        id="s1",
        category="c1",
        severity="low",
        target="email",
        payload="hack",
        placement="body",
        success_criteria="none",
    )

    variants = mutator.generate_variants(seed, num_variants=200)

    assert len(variants) == 200
    assert len(mutator.lineage) == 200
    assert mutator.lineage[variants[0].id] == "s1"
    # Ensure deduplication works (all 200 are unique)
    assert len({v.payload for v in variants}) == 200


def test_injector():
    provider = MockProvider()
    agent = EmailAgent(llm=provider)

    attack = Attack(
        id="a1",
        category="c",
        severity="low",
        target="email",
        payload="EVIL_INJECT",
        placement="email_body",
        success_criteria="none",
    )

    assert "EVIL_INJECT" not in agent.inbox["msg_1"]["body"]
    InjectionEngine.inject(agent, attack)
    assert "EVIL_INJECT" in agent.inbox["msg_1"]["body"]
