from pyDatalog import pyDatalog
from hechos_datalog import *

#cargar hechos en memoria
cargar_hechos()

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

adjudicacion_repetida(O, P) <= (adjudicaciones_proveedor_org[O, P] > 3)


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

proveedor_exclusivo(P, O) <= (
    (cant_organismos_proveedor[P] == 1) &
    (proveedor_de[X] == P) &
    (organismo_de[X] == O)
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

