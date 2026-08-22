from datetime import date

import pandas as pd
import streamlit as st

from funciones_campo_SPE import (
    calcular_plan_mensual,
    calcular_produccion_diferida,
    calcular_produccion_real,
    cargar_planificacion,
    grafico_barras_diferida,
    grafico_comparacion,
    grafico_linea,
)


# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================

st.title("Campo SPE | Plan Operativo y Producción Diferida")

st.write(
    "Aplicación para revisar el Plan Operativo Anual del Campo SPE y estimar "
    "la producción diferida causada por eventos operacionales."
)

with st.expander("Guía rápida"):
    st.markdown(
        """
        1. Carga el Excel del Plan Operativo Anual.
        2. Revisa la producción planificada.
        3. Registra eventos operacionales.
        4. Compara el plan contra la producción real estimada.

        **Fórmula:** producción diferida = BPD afectado x horas de parada / 24.
        """
    )


# ============================================================
# CARGA DEL ARCHIVO
# ============================================================

archivo = st.file_uploader(
    "Cargar Plan Operativo Anual del Campo SPE",
    type=["xlsx"],
)

if archivo is None:
    st.info("Carga el archivo Excel para comenzar.")
    st.stop()

plan = cargar_planificacion(archivo)
resumen_plan = calcular_plan_mensual(plan)


# ============================================================
# MEMORIA TEMPORAL DE LA APP
# ============================================================

if "eventos" not in st.session_state:
    st.session_state.eventos = []

if "ultimo_detalle" not in st.session_state:
    st.session_state.ultimo_detalle = None

if "archivo_actual" not in st.session_state:
    st.session_state.archivo_actual = archivo.name

if st.session_state.archivo_actual != archivo.name:
    st.session_state.archivo_actual = archivo.name
    st.session_state.eventos = []
    st.session_state.ultimo_detalle = None


# ============================================================
# MÓDULOS DE LA APLICACIÓN
# ============================================================

modulo_1, modulo_2, modulo_3 = st.tabs(
    [
        "1. Plan Operativo Anual",
        "2. Eventos",
        "3. Plan vs. Real estimada",
    ]
)


# ============================================================
# MÓDULO 1: PLAN OPERATIVO
# ============================================================

with modulo_1:
    st.subheader("Plan Operativo Anual")
    st.write("Primero revisamos la planificación mensual del campo.")

    st.dataframe(plan, use_container_width=True, hide_index=True)

    plan_anual = resumen_plan["Plan_bbl"].sum()
    max_bpd = resumen_plan["Plan_BPD"].max()
    min_bpd = resumen_plan["Plan_BPD"].min()

    c1, c2, c3 = st.columns(3)
    c1.metric("Plan anual", f"{plan_anual:,.0f} bbl")
    c2.metric("Máximo mensual", f"{max_bpd:,.0f} BPD")
    c3.metric("Mínimo mensual", f"{min_bpd:,.0f} BPD")

    st.plotly_chart(
        grafico_linea(
            resumen_plan["Mes"],
            resumen_plan["Plan_BPD"],
            "Plan",
            "Producción mensual planificada",
            "Producción planificada (BPD)",
            escalon=True,
        ),
        use_container_width=True,
    )

    st.plotly_chart(
        grafico_linea(
            resumen_plan["Mes"],
            resumen_plan["Plan_acumulado_bbl"],
            "Plan acumulado",
            "Producción acumulada planificada",
            "Producción acumulada (bbl)",
        ),
        use_container_width=True,
    )

    tabla_plan = resumen_plan[
        ["Mes", "Dias_mes", "Plan_BPD", "Plan_bbl", "Plan_acumulado_bbl"]
    ].copy()

    tabla_plan.columns = [
        "Mes", "Días", "Plan BPD", "Plan mensual bbl", "Plan acumulado bbl"
    ]

    st.dataframe(tabla_plan, use_container_width=True, hide_index=True)


# ============================================================
# MÓDULO 2: EVENTOS OPERACIONALES
# ============================================================

with modulo_2:
    st.subheader("Eventos operacionales")
    st.write("Registra una parada para estimar los barriles diferidos.")

    with st.form("form_evento"):
        col1, col2 = st.columns(2)

        with col1:
            fecha_evento = st.date_input(
                "Fecha del evento",
                value=date(2026, 1, 15),
                min_value=date(2026, 1, 1),
                max_value=date(2026, 12, 31),
            )

            tipo_evento = st.selectbox(
                "Tipo de evento",
                [
                    "Problema eléctrico",
                    "Falla mecánica",
                    "Restricción operacional",
                    "Problema de facilidades",
                    "Otro",
                ],
            )

        with col2:
            pozos_afectados = st.multiselect(
                "Pozos afectados",
                options=plan["Pozo"].tolist(),
            )

            horas_parada = st.number_input(
                "Horas de parada",
                min_value=0.5,
                max_value=24.0,
                value=8.0,
                step=0.5,
            )

        registrar = st.form_submit_button("Registrar evento")

    if registrar:
        if len(pozos_afectados) == 0:
            st.warning("Selecciona al menos un pozo afectado.")
        else:
            evento, detalle = calcular_produccion_diferida(
                plan,
                fecha_evento,
                pozos_afectados,
                horas_parada,
                tipo_evento,
            )

            st.session_state.eventos.append(evento)
            st.session_state.ultimo_detalle = detalle

            st.success(
                f"Evento registrado. Producción diferida estimada: "
                f"{evento['Diferida_bbl']:,.2f} bbl"
            )

    if st.session_state.ultimo_detalle is not None:
        with st.expander("Detalle del último evento"):
            detalle_mostrar = st.session_state.ultimo_detalle.copy()
            detalle_mostrar["Diferida_bbl"] = detalle_mostrar["Diferida_bbl"].round(2)
            st.dataframe(detalle_mostrar, use_container_width=True, hide_index=True)

    if len(st.session_state.eventos) == 0:
        st.info("Todavía no se han registrado eventos.")
    else:
        eventos_df = pd.DataFrame(st.session_state.eventos)
        resultado = calcular_produccion_real(resumen_plan, st.session_state.eventos)
        total_diferida = eventos_df["Diferida_bbl"].sum()

        e1, e2, e3 = st.columns(3)
        e1.metric("Eventos registrados", len(eventos_df))
        e2.metric("Producción diferida total", f"{total_diferida:,.2f} bbl")
        e3.metric("Pozos del campo", len(plan))

        tabla_eventos = eventos_df[
            ["Fecha", "Mes", "Evento", "Pozos", "Horas", "Diferida_bbl"]
        ].copy()

        tabla_eventos["Diferida_bbl"] = tabla_eventos["Diferida_bbl"].round(2)
        st.dataframe(tabla_eventos, use_container_width=True, hide_index=True)

        if st.button("Limpiar todos los eventos"):
            st.session_state.eventos = []
            st.session_state.ultimo_detalle = None
            st.rerun()

        st.plotly_chart(
            grafico_linea(
                resultado["Mes"],
                resultado["Real_estimado_BPD"],
                "Real estimada",
                "Producción mensual real estimada",
                "Producción (BPD promedio mensual)",
                escalon=True,
            ),
            use_container_width=True,
        )


# ============================================================
# MÓDULO 3: PLAN VS. REAL ESTIMADA
# ============================================================

with modulo_3:
    st.subheader("Plan vs. Real estimada")

    resultado = calcular_produccion_real(resumen_plan, st.session_state.eventos)

    plan_total = resultado["Plan_bbl"].sum()
    real_total = resultado["Real_estimado_bbl"].sum()
    diferida_total = resultado["Diferida_bbl"].sum()
    cumplimiento = real_total / plan_total * 100

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Plan anual", f"{plan_total:,.0f} bbl")
    k2.metric("Real estimada", f"{real_total:,.0f} bbl")
    k3.metric("Producción diferida", f"{diferida_total:,.0f} bbl")
    k4.metric("Cumplimiento", f"{cumplimiento:,.2f} %")

    st.plotly_chart(
        grafico_comparacion(resultado),
        use_container_width=True,
    )

    st.plotly_chart(
        grafico_comparacion(resultado, acumulado=True),
        use_container_width=True,
    )

    st.plotly_chart(
        grafico_barras_diferida(resultado),
        use_container_width=True,
    )

    tabla_final = resultado[
        [
            "Mes",
            "Plan_BPD",
            "Plan_bbl",
            "Diferida_bbl",
            "Real_estimado_BPD",
            "Real_estimado_bbl",
            "Plan_acumulado_bbl",
            "Real_acumulado_bbl",
            "Cumplimiento_pct",
        ]
    ].copy()

    tabla_final.columns = [
        "Mes",
        "Plan BPD",
        "Plan mensual bbl",
        "Diferida bbl",
        "Real estimada BPD",
        "Real estimada mensual bbl",
        "Plan acumulado bbl",
        "Real acumulado bbl",
        "Cumplimiento %",
    ]

    columnas_numericas = [
        "Plan BPD",
        "Plan mensual bbl",
        "Diferida bbl",
        "Real estimada BPD",
        "Real estimada mensual bbl",
        "Plan acumulado bbl",
        "Real acumulado bbl",
        "Cumplimiento %",
    ]

    for columna in columnas_numericas:
        tabla_final[columna] = tabla_final[columna].round(2)

    st.dataframe(tabla_final, use_container_width=True, hide_index=True)
