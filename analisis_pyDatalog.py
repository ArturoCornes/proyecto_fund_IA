from pyDatalog import pyDatalog
from hechos_datalog import *

#cargar hechos en memoria
cargar_hechos()

#region Proveedor Frecuente
#crear términos nuevos
pyDatalog.create_terms('X, P, O, N, C,compra_grande,proveedor_frecuente, cantidad_adjudicaciones')


# cantidad de adjudicaciones por proveedor
(cantidad_adjudicaciones[P] == len_(X)) <= ( proveedor_de[X] == P )

# regla
proveedor_frecuente(P) <= (cantidad_adjudicaciones[P] > 10)

#endregion

#region Alta concentracion

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
#print(alta_concentracion(O, P))

#endregion

#region Adjudicacion Repetida
pyDatalog.create_terms(
    '''
    X, O, P, C,
    adjudicaciones_proveedor_org,
    adjudicacion_repetida
    '''
)

#funcion
(adjudicaciones_proveedor_org[O, P] == len_(X)) <= (
    (organismo_de[X] == O) &
    (proveedor_de[X] == P) &
    (P != 'NAN')
)

#regla
adjudicacion_repetida(O, P) <= (adjudicaciones_proveedor_org[O, P] > 3)

#consulta
#print(adjudicaciones_proveedor_org[O, P] == C)

#endregion

