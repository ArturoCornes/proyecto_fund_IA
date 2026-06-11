import unittest
from Pipeline import Pipeline, Stage
from PrologWrapper import Query, Fact
from PyDatalogWrapper import PyDatalogWrapper
from Orchestrator import Orchestrator


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
            rule_file="datos_datalog.py",
            queries=[Query("extraer_datos_para_prolog")],
            outputs=[],
            depends_on=[]
        )

        # --- Stage 2: Prolog (fraud detection) ---
        # Facts produced by PyDatalog will be added to Prolog KB
        prolog_outputs = [
            Fact("transaccion", "tx_001", "juan", 15000),
            Fact("transaccion", "tx_002", "maria", 500),
            Fact("transaccion", "tx_003", "pedro", 65000),
            Fact("transaccion", "tx_004", "juan", 200),
            Fact("transaccion", "tx_005", "lucia", 9000),
            Fact("cuenta_sospechosa", "juan"),
            Fact("cuenta_sospechosa", "carlos"),
        ]

        prolog_stage = Stage(
            name="detect_fraud",
            engine="prolog",
            rule_file="reglas.pl",
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

        # PyDatalog stage should have returned the extracted data dict
        pydatalog_result = results[0]
        self.assertIsNotNone(pydatalog_result)
        print("\n=== PyDatalog Result ===")
        print(pydatalog_result)

        # Prolog stage should have found fraud alerts
        prolog_result = results[1]
        self.assertGreater(len(prolog_result), 0, "Prolog should detect at least one fraud alert")

        print("\n=== Prolog Fraud Alerts ===")
        for query_result in prolog_result:
            print(query_result)

        # Verify expected fraud detections
        all_alerts = []
        for qr in prolog_result:
            if qr.return_val:
                for alert in qr.return_val:
                    all_alerts.append(alert)

        # tx_001 (juan, $15000) -> "Monto alto en cuenta sospechosa" (juan is suspicious, > 10k)
        # tx_003 (pedro, $65000) -> "Transaccion masiva - Posible lavado" (> 50k)
        # tx_004 (juan, $200) -> "Movimiento de cuenta en vigilancia" (juan is suspicious, <= 10k)
        alert_messages = [a.get("Alerta", "") for a in all_alerts]

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


if __name__ == "__main__":
    unittest.main()
