:- dynamic adjudica/3.
:- dynamic total_adjudicaciones/2.
:- dynamic tiempo_de_adjudicacion/3.
:- dynamic promedio_general_tiempo_adjudicaciones/1.

% Hechos esperados desde orquestrador.py:
%   adjudica(Organismo, Proveedor, Cantidad).
%   total_adjudicaciones(Organismo, Total).
%   tiempo_de_adjudicacion(Organismo, Proveedor, TiempoPromedio).
%   promedio_general_tiempo_adjudicaciones(PromedioGeneral).

umbral_concentracion(40).
umbral_repeticion(3).
factor_sobretiempo(1.5).

porcentaje_concentracion(Organismo, Proveedor, Porcentaje) :-
    adjudica(Organismo, Proveedor, Cantidad),
    total_adjudicaciones(Organismo, Total),
    Total > 0,
    Porcentaje is (Cantidad * 100) / Total.

riesgo_concentracion(Organismo, Proveedor, Porcentaje) :-
    porcentaje_concentracion(Organismo, Proveedor, Porcentaje),
    umbral_concentracion(Umbral),
    Porcentaje >= Umbral.

adjudicacion_repetida(Organismo, Proveedor, Cantidad) :-
    adjudica(Organismo, Proveedor, Cantidad),
    umbral_repeticion(Umbral),
    Cantidad > Umbral.

alerta_sobretiempo(Organismo, Proveedor, Tiempo, PromedioGeneral) :-
    tiempo_de_adjudicacion(Organismo, Proveedor, Tiempo),
    promedio_general_tiempo_adjudicaciones(PromedioGeneral),
    factor_sobretiempo(Factor),
    PromedioGeneral > 0,
    Tiempo > PromedioGeneral * Factor.

recomendar_auditoria(Organismo) :-
    recomendar_auditoria(Organismo, _, _).

recomendar_auditoria(Organismo, Proveedor, motivo(concentracion, Porcentaje)) :-
    riesgo_concentracion(Organismo, Proveedor, Porcentaje).

recomendar_auditoria(Organismo, Proveedor, motivo(repeticion, Cantidad)) :-
    adjudicacion_repetida(Organismo, Proveedor, Cantidad).

recomendar_auditoria(Organismo, Proveedor, motivo(sobretiempo, Tiempo)) :-
    alerta_sobretiempo(Organismo, Proveedor, Tiempo, _).
