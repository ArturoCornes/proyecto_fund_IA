import unittest
from pathlib import Path

from logiflow import Orchestrator, Pipeline, Stage, Query, Fact

_TEST_DIR = Path(__file__).resolve().parent


class TestOrchestrator(unittest.TestCase):

    def setUp(self):
        self.pipeline = Pipeline()
        self.orchestrator = Orchestrator()

    def test_pydatalog_then_prolog_pipeline(self):
        """
        Pipeline flow:
          1. PyDatalog stage: extracts transaction data and suspicious accounts
          2. Prolog stage: loads fraud detection rules, adds extracted facts, runs queries
        """
        # --- Stage 1: PyDatalog (extracts data) ---
        pydatalog_stage = Stage(
            name="extract_data",
            engine="pydatalog",
            rule_file=str(_TEST_DIR / "datos.dl"),
            queries=[
                Query("transaccion(Tx, Usuario, Monto)"),
                Query("cuenta_sospechosa(Usuario)")
            ],
            outputs=[],
            depends_on=[]
        )

        # --- Stage 2: Prolog (fraud detection) ---
        # Facts produced by PyDatalog will be added to Prolog KB automatically via pipeline
        prolog_outputs = []

        prolog_stage = Stage(
            name="detect_fraud",
            engine="prolog",
            rule_file=str(_TEST_DIR / "reglas.pl"),
            queries=[
                Query("alerta_fraude(TxID, Usuario, Alerta)"),
            ],
            outputs=prolog_outputs,
            depends_on=[pydatalog_stage]
        )

        self.pipeline.add_stage(pydatalog_stage)
        self.pipeline.add_stage(prolog_stage)

        # Run the pipeline
        results = self.orchestrator.run_pipeline(self.pipeline)

        # --- Assertions ---
        self.assertEqual(len(results), 2, "Pipeline should return results for both stages")

        # PyDatalog stage should have returned a KnowledgeSet
        pydatalog_ks = results[0]
        self.assertIsNotNone(pydatalog_ks)
        print("\n=== PyDatalog KnowledgeSet ===")
        print(pydatalog_ks)

        # Prolog stage should have returned a KnowledgeSet of fraud alerts
        prolog_ks = results[1]
        self.assertIsNotNone(prolog_ks)

        print("\n=== Prolog Fraud Alerts KnowledgeSet ===")
        print(prolog_ks)

        # Verify expected fraud detections in the KnowledgeSet under "alerta_fraude"
        alerts = prolog_ks.facts.get("alerta_fraude", [])
        
        self.assertGreater(len(alerts), 0, "Prolog should detect at least one fraud alert")

        # In KnowledgeSet, alerts are tuples of (TxID, Usuario, Alerta)
        alert_messages = [a[2] for a in alerts]

        self.assertTrue(
            any("Monto alto en cuenta sospechosa" in msg for msg in alert_messages),
            "Should detect tx_001 as high amount on suspicious account"
        )
        self.assertTrue(
            any("Transaccion masiva" in msg for msg in alert_messages),
            "Should detect tx_003 as massive transaction"
        )
        self.assertTrue(
            any("vigilancia" in msg for msg in alert_messages),
            "Should detect tx_004 as suspicious account movement"
        )

        print("\n=== All Fraud Alerts Detected ===")
        for msg in alert_messages:
            print(f"  - {msg}")

    def test_circular_dependency(self):
        stage1 = Stage("S1", "pydatalog", None, [], [], [])
        stage2 = Stage("S2", "pydatalog", None, [], [], [stage1])
        stage1.depends_on.append(stage2) # Create cycle
        
        pipeline = Pipeline()
        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)
        
        with self.assertRaises(RecursionError):
            self.orchestrator.run_pipeline(pipeline)

if __name__ == "__main__":
    unittest.main()
