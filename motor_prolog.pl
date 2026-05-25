% -----gen by pydatalog and loaded here----
adjudica(EntidadGubernamental,Provedor,Cantidad).
tiempo_de_adjudicacion(EntidadGubernamental,Provedor,Tiempo).
promedio_general_tiempo_adjudicaciones(Tiempo).
% -----------------------------------------

riesgo_concentracion(EntidadGubernamental,N) :- 
    adjudica(EntidadGubernamental,Provedor,Cantidad), 
    Cantidad > N.

recomendar_auditoria(EntidadGubernamental):-
    riesgo_concentracion(EntidadGubernamental,100).

alerta_sobretiempo(EntidadGubernamental):-
    tiempo_de_adjudicacion(EntidadGubernamental,Provedor,Tiempo),
    promedio_general_tiempo_adjudicaciones(T),
    Tiempo > T.