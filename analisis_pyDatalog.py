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

def get_provedores_frecuentes():
    """returns P:~iterable"""
    return proveedor_frecuente(P)
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

def get_orgs_con_alta_concentracion():
    """returns O and P: ~iterables"""
    return alta_concentracion(O, P)

#consulta
# print(alta_concentracion(O, P))

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

def get_orgs_con_adjudicacion_repetida():
    """returns O and P: ~iterables"""
    return adjudicacion_repetida(O, P)

#consulta
#print(adjudicaciones_proveedor_org[O, P] == C)
#endregion

#region DemoraAdjudicion
pyDatalog.create_terms("media_dias, Dias, ID")
(media_dias[None] == mean_(Dias, for_each=ID)) <= (
    (compra[ID]) & (dias_adj_de[ID] == Dias) & (Dias != None)
    ) 

def get_media_dias():
    """returns O and P: ~iterables"""
    return media_dias[None]
# endregion