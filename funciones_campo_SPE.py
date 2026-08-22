import pandas as pd
import plotly.graph_objects as go


MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

DIAS_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def cargar_planificacion(archivo):
    plan = pd.read_excel(archivo)
    return plan


def calcular_plan_mensual(plan):
    total_bpd = plan[MESES].sum()

    resumen = pd.DataFrame({
        "Mes": MESES,
        "Dias_mes": DIAS_MES,
        "Plan_BPD": total_bpd.values,
    })

    resumen["Plan_bbl"] = resumen["Plan_BPD"] * resumen["Dias_mes"]
    resumen["Plan_acumulado_bbl"] = resumen["Plan_bbl"].cumsum()

    return resumen


def calcular_produccion_diferida(plan, fecha_evento, pozos_afectados, horas_parada, tipo_evento):
    posicion_mes = fecha_evento.month - 1
    mes = MESES[posicion_mes]

    detalle = plan[
        plan["Pozo"].isin(pozos_afectados)
    ][["Pozo", mes]].copy()

    detalle.columns = ["Pozo", "Plan_BPD"]
    detalle["Horas_parada"] = horas_parada
    detalle["Diferida_bbl"] = detalle["Plan_BPD"] * horas_parada / 24

    total_diferida = detalle["Diferida_bbl"].sum()
    tasa_afectada = detalle["Plan_BPD"].sum()

    evento = {
        "Fecha": fecha_evento,
        "Mes": mes,
        "Evento": tipo_evento,
        "Pozos": ", ".join(pozos_afectados),
        "N_pozos": len(pozos_afectados),
        "Horas": horas_parada,
        "Tasa_afectada_BPD": tasa_afectada,
        "Diferida_bbl": total_diferida,
    }

    return evento, detalle


def calcular_produccion_real(resumen_plan, eventos):
    resultado = resumen_plan.copy()
    resultado["Diferida_bbl"] = 0.0

    for evento in eventos:
        mes_evento = evento["Mes"]
        barriles_diferidos = evento["Diferida_bbl"]
        fila_del_mes = resultado["Mes"] == mes_evento

        resultado.loc[
            fila_del_mes,
            "Diferida_bbl"
        ] = resultado.loc[fila_del_mes, "Diferida_bbl"] + barriles_diferidos

    resultado["Real_estimado_bbl"] = resultado["Plan_bbl"] - resultado["Diferida_bbl"]
    resultado["Real_estimado_bbl"] = resultado["Real_estimado_bbl"].clip(lower=0)
    resultado["Real_estimado_BPD"] = resultado["Real_estimado_bbl"] / resultado["Dias_mes"]
    resultado["Real_acumulado_bbl"] = resultado["Real_estimado_bbl"].cumsum()
    resultado["Cumplimiento_pct"] = resultado["Real_estimado_bbl"] / resultado["Plan_bbl"] * 100
    resultado["Cumplimiento_pct"] = resultado["Cumplimiento_pct"].fillna(0)

    return resultado


def grafico_linea(x, y, nombre, titulo, eje_y, escalon=False):
    fig = go.Figure()
    forma_linea = "linear"

    if escalon:
        forma_linea = "hv"

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name=nombre,
            line_shape=forma_linea,
        )
    )

    fig.update_layout(
        title=titulo,
        xaxis_title="Mes",
        yaxis_title=eje_y,
        hovermode="x unified",
        height=430,
    )

    return fig


def grafico_comparacion(resultado, acumulado=False):
    fig = go.Figure()

    if acumulado:
        columna_plan = "Plan_acumulado_bbl"
        columna_real = "Real_acumulado_bbl"
        titulo = "Producción acumulada: Plan vs. Real estimada"
        eje_y = "Producción acumulada (bbl)"
        forma_linea = "linear"
    else:
        columna_plan = "Plan_BPD"
        columna_real = "Real_estimado_BPD"
        titulo = "Producción mensual: Plan vs. Real estimada"
        eje_y = "Producción (BPD promedio mensual)"
        forma_linea = "hv"

    fig.add_trace(
        go.Scatter(
            x=resultado["Mes"],
            y=resultado[columna_plan],
            mode="lines+markers",
            name="Plan",
            line_shape=forma_linea,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=resultado["Mes"],
            y=resultado[columna_real],
            mode="lines+markers",
            name="Real estimada",
            line_shape=forma_linea,
        )
    )

    fig.update_layout(
        title=titulo,
        xaxis_title="Mes",
        yaxis_title=eje_y,
        hovermode="x unified",
        height=450,
        legend_title_text="Serie",
    )

    return fig


def grafico_barras_diferida(resultado):
    fig = go.Figure(
        go.Bar(
            x=resultado["Mes"],
            y=resultado["Diferida_bbl"],
            name="Producción diferida",
        )
    )

    fig.update_layout(
        title="Producción diferida por mes",
        xaxis_title="Mes",
        yaxis_title="Producción diferida (bbl)",
        height=420,
    )

    return fig
