python preparar_dataset.py --input compras_publicas.csv   # → compras_procesadas.csv
python etl.py --input compras_procesadas.csv              # → compras.db + hechos_datalog.py