#region 1) Proveedor Frecuente
#crear términos nuevos
pyDatalog.create_terms('X, P, O, N, C,compra_grande,proveedor_frecuente, cantidad_adjudicaciones')


# cantidad de adjudicaciones por proveedor
(cantidad_adjudicaciones[P] == len_(X)) <= ( proveedor_de[X] == P )

# regla
proveedor_frecuente(P) <= (cantidad_adjudicaciones[P] > 10)

#endregion

#region 2) Alta concentracion

pyDatalog.create_terms(
    '''
    X, O, P, C1, C2,
    adjudicaciones_org,
    adjudicaciones_proveedor_org,
    porcentaje_concentracion,
    alta_concentracion
    '''
)

#funcion
(adjudicaciones_org[O] == len_(X)) <= (organismo_de[X] == O)


(adjudicaciones_proveedor_org[O, P] == len_(X)) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (P != 'NAN')
)

#regla
alta_concentracion(O, P) <= (
    (adjudicaciones_proveedor_org[O, P] * 100)
    / adjudicaciones_org[O] > 40
)


#consulta
# print(alta_concentracion(O, P))

#endregion

#region 3) Adjudicacion Repetida
pyDatalog.create_terms(
    '''
    O, P,
    adjudicacion_repetida
    '''
)


#regla
#cambiar nombre a proveedor_recurrente
adjudicacion_repetida(O, P) <= (adjudicaciones_proveedor_org[O, P] > 3)

#mask for prolog compatibility
adjudica(O, P, C) <= (adjudicaciones_proveedor_org[O, P] == C)

#consulta
#print(adjudicaciones_proveedor_org[O, P] == C)

#endregion

#region 4) organismos con baja cantidad de distintos proveedores

pyDatalog.create_terms('''
X, O, P,
cantidad_proveedores_org                       
''')


# Cantidad de proveedores distintos del organismo
(cantidad_proveedores_org[O] == len_(P)) <= (
    organismo_de[X] == O
) & (
    proveedor_de[X] == P
) & (
    P != 'NAN'
)

#mask for prolog compatibility
total_adjudicaciones(O, C) <= (cantidad_proveedores_org[O] == C)

#endregion


#region 5) proveedores exclusivos

pyDatalog.create_terms('''
X, O, P,
cant_organismos_proveedor,
proveedor_exclusivo                       
''')


(cant_organismos_proveedor[P] == len_(O)) <= (
    proveedor_de[X] == P
) & (
    organismo_de[X] == O
)

proveedor_exclusivo(P) <= (
    cant_organismos_proveedor[P] == 1
)

#endregion

#region 6) Proveedor dominantes en la Organizacion

pyDatalog.create_terms('''
X, O, P,
cantidad_adjudicaciones_org,
porcentaje_adjudicaciones,
proveedor_dominante
''')

(cantidad_adjudicaciones_org[O] == len_(X)) <= (organismo_de[X] == O)

(porcentaje_adjudicaciones[O, P] ==
    (adjudicaciones_proveedor_org[O, P] * 100.0) /
    cantidad_adjudicaciones_org[O]
)


pyDatalog.create_terms('N,T,Porcentaje')
(porcentaje_adjudicaciones[O,P] == Porcentaje) <= (
    (adjudicaciones_proveedor_org[O,P] == N) &
    (cantidad_adjudicaciones_org[O] == T) &
    (Porcentaje == (N * 100.0) / T)
)



#endregion


#region 7) cantidad de organizaciones al que brinda cada proveedor

pyDatalog.create_terms('''
X,O,P,N,
cantidad_organismos_proveedor,
proveedor_ubicuo,
cantidad_total_organismos
''')

(cantidad_organismos_proveedor[P] == len_(O)) <= (
    proveedor_de[X] == P
) & (
    organismo_de[X] == O
) & (
    P != 'NAN'
)

(cantidad_total_organismos[None] == len_(O)) <= (
    organismo_de[X] == O
)

pyDatalog.create_terms('Total, Cant, Porcentaje, cobertura_organismos,proveedor_muy_extendido')

(cobertura_organismos[P] == Porcentaje) <= (
    (cantidad_organismos_proveedor[P] == Cant) &
    (cantidad_total_organismos[None] == Total) &
    (Porcentaje == (Cant * 100.0) / Total)
)

proveedor_muy_extendido(P) <= (
    (cobertura_organismos[P] == Porcentaje) &
    (Porcentaje > 25)
)



#endregion




#region 8) Proveedores con % de datos faltantes en dias_adj_de
pyDatalog.create_terms('''
X,Y, P,
total_adj_proveedor,
adj_sin_dias_proveedor,
porcentaje_faltantes_proveedor,
Total,
Faltantes,
Porcentaje
''')

# Total de adjudicaciones del proveedor
(total_adj_proveedor[P] == len_(X)) <= (
    proveedor_de[X] == P
)

# Adjudicaciones sin dias_adj
(adj_sin_dias_proveedor[P] == len_(X)) <= (
    (proveedor_de[X] == P) &
    (dias_adj_de[X] == None)
)

# Porcentaje de faltantes
(porcentaje_faltantes_proveedor[P] == Porcentaje) <= (
    (total_adj_proveedor[P] == Total) &
    (adj_sin_dias_proveedor[P] == Faltantes) &
    (Porcentaje == (Faltantes * 100.0) / Total)
)


#endregion


#region 9) Gastos de Organismo

pyDatalog.create_terms('''
X, O, M,
gasto_total_organismo
''')


(gasto_total_organismo[O] == sum_(M, for_each=X)) <= (
    (organismo_de[X] == O) &
    (monto_de[X] == M) &
    (M != None)
)



#endregion*


#region 10) Concentracion economica del organismo en un proveedor

pyDatalog.create_terms('''
X,O,P,M,
monto_total_organismo
''')

(monto_total_organismo[O] == sum_(M, for_each=X)) <= (
    (organismo_de[X] == O) &
    (monto_de[X] == M) &
    (M != None)
)

pyDatalog.create_terms('''
monto_proveedor_organismo
''')

(monto_proveedor_organismo[O,P] == sum_(M, for_each=X)) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (monto_de[X] == M) &
    (M != None)
)


pyDatalog.create_terms('''
TotalMonto,
MontoProveedor,
PorcentajeMonto,
porcentaje_monto_proveedor
''')

(porcentaje_monto_proveedor[O,P] == PorcentajeMonto) <= (
    (monto_total_organismo[O] == TotalMonto) &
    (monto_proveedor_organismo[O,P] == MontoProveedor) &
    (PorcentajeMonto == (MontoProveedor * 100.0) / TotalMonto)
)

#endregion



# region 11) dias adjudicacion
pyDatalog.create_terms('''
    X, O, P, D, S,
    suma_dias_op, 
    cant_adjudicaciones_op, 
    tiempo_de_adjudicacion,
    suma_dias_op,
    TiempoPromedio
''')

(suma_dias_op[O, P] == sum_(D, for_each=X)) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (dias_adj_de[X] == D) &
    (D != None)
)

(cant_adjudicaciones_op[O, P] == len_(X)) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (dias_adj_de[X] != None)
)

tiempo_de_adjudicacion(O, P, TiempoPromedio) <= (
    (suma_dias_op[O, P] == S) &
    (cant_adjudicaciones_op[O, P] == C) &
    (C > 0) & 
    (TiempoPromedio == S / C)
)

#endregion

#region 12) promedio general dias adj

pyDatalog.create_terms('''
    X, D, S, C,
    total_dias_global, 
    cant_adjudicaciones_global, 
    promedio_general_tiempo_adjudicaciones,
    PromedioGeneral
''')

(total_dias_global[None] == sum_(D, for_each=X)) <= (
    (dias_adj_de[X] == D) &
    (D != None)
)

(cant_adjudicaciones_global[None] == len_(X)) <= (
    (dias_adj_de[X] != None)
)

promedio_general_tiempo_adjudicaciones(PromedioGeneral) <= (
    (total_dias_global[None] == S) &
    (cant_adjudicaciones_global[None] == C) &
    (C > 0) &
    (PromedioGeneral == S / C)
)

#region 13) Gasto total por proveedor

pyDatalog.create_terms('''
X, P, M,
gasto_total_proveedor
''')

(gasto_total_proveedor[P] == sum_(M, for_each=X)) <= (
    (proveedor_de[X] == P) &
    (monto_de[X] == M) &
    (M != None)
)

#endregion

#region 13) Proveedores por organizacion
pyDatalog.create_terms('''
X, O, P,
proveedor_organismo
''')

proveedor_organismo(O, P) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (P != 'NAN')
)

print(proveedor_organismo(O, P))

#endregion


