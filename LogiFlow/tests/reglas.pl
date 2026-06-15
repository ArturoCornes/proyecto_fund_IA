% Regla 1: Es fraude si la cuenta está marcada como sospechosa y mueve más de $10,000
alerta_fraude(TxID, Usuario, "Monto alto en cuenta sospechosa") :- 
    transaccion(TxID, Usuario, Monto),
    cuenta_sospechosa(Usuario),
    Monto > 10000.

% Regla 2: Es fraude si cualquier transacción supera los $50,000 (evasión de controles)
alerta_fraude(TxID, Usuario, "Transaccion masiva - Posible lavado") :- 
    transaccion(TxID, Usuario, Monto),
    Monto > 50000.

% Regla 3: Alerta preventiva si un usuario sospechoso hace cualquier movimiento
alerta_fraude(TxID, Usuario, "Movimiento de cuenta en vigilancia") :-
    transaccion(TxID, Usuario, Monto),
    cuenta_sospechosa(Usuario),
    Monto =< 10000.