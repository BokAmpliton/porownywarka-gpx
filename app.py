import io
import streamlit as st
import gpxpy
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime
 
def load_gpx(uploaded_file):
    gpx = gpxpy.parse(uploaded_file)
    points = []
    elevations = []
    times = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))
                if point.elevation is not None:
                    elevations.append(point.elevation)
                if point.time:
                    times.append(point.time)
    return points, elevations, times
 
def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
 
def track_length(points):
    dist = 0
    for i in range(1, len(points)):
        dist += haversine(*points[i-1], *points[i])
    return dist
 
def format_duration(start, end):
    delta = end - start
    mins, secs = divmod(delta.seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours} godz {mins} min {secs} sek"
    elif mins > 0:
        return f"{mins} min {secs} sek"
    else:
        return f"{secs} sek"
 
st.set_page_config(layout="wide")
 
st.title("Porównywarka tras GPX")
uploaded_files = st.file_uploader("Wgraj pliki GPX do porównania", type="gpx", accept_multiple_files=True)
 
if uploaded_files:
    data = []
    colors = ['blue', 'red', 'orange', 'green', 'purple', 'brown', 'yellow', 'pink', 'gray', 'black']
    # Powtarzamy kolory jeśli jest więcej tras
    while len(colors) < len(uploaded_files):
        colors = colors + colors
 
    for i, f in enumerate(uploaded_files):
        points, elev, times = load_gpx(f)
        if not points:
            continue
        start_time = min(times) if times else None
        end_time = max(times) if times else None
        duration = format_duration(start_time, end_time) if start_time and end_time else "brak danych"
        dist = track_length(points)
        elev_diff = np.ptp(elev) if elev else 0
        data.append({
            "name": f.name,
            "points": points,
            "elev": elev,
            "start": start_time,
            "end": end_time,
            "duration": duration,
            "distance": dist,
            "elev_diff": elev_diff,
            "color": colors[i],
        })
 
    # Wybór trasy do wyświetlenia (lub wszystkie)
    options = ["Wszystkie"] + [d["name"] for d in data]
    selected_route = st.selectbox("Wybierz trasę do wyświetlenia na mapie", options)
 
    # Kolumny na mapę i podsumowanie
    col1, col2 = st.columns([2.5,2.2])
    with col1:
        # Jeśli wybrano jedną trasę, pokazujemy tylko ją, inaczej wszystkie
        if selected_route == "Wszystkie":
            m = folium.Map(location=data[0]["points"][0], zoom_start=13, tiles="OpenStreetMap")
            for d in data:
                folium.PolyLine(d["points"], color=d["color"], weight=4, opacity=0.7, tooltip=d["name"]).add_to(m)
        else:
            selected_data = next(d for d in data if d["name"] == selected_route)
            m = folium.Map(location=selected_data["points"][0], zoom_start=13, tiles="OpenStreetMap")
            folium.PolyLine(selected_data["points"], color=selected_data["color"], weight=6, opacity=1, tooltip=selected_data["name"]).add_to(m)
        st_folium(m, width=1000, height=600)
 
    with col2:
        # Wyświetlamy podsumowanie w tabeli
        import pandas as pd
        df = pd.DataFrame([{
            "Kolor": f'<div style="width:20px; height:20px; background-color:{d["color"]}; border-radius: 3px;"></div>',
            "Nazwa pliku": d["name"],
            "Start": d["start"].strftime("%Y-%m-%d %H:%M:%S") if d["start"] else "brak danych",
            "Koniec": d["end"].strftime("%Y-%m-%d %H:%M:%S") if d["end"] else "brak danych",
            "Czas aktywności": d["duration"],
            "Długość (km)": round(d["distance"], 2),
            "Przewyższenie (m)": round(d["elev_diff"], 1),
        } for d in data])
        st.markdown("### Podsumowanie tras")

        # DataFrame do tabeli HTML (z kolorem)
        df = pd.DataFrame([{
            "Kolor": f'<div style="width:20px; height:20px; background-color:{d["color"]}; border-radius: 3px;"></div>',
            "Nazwa pliku": d["name"],
            "Start": d["start"].strftime("%Y-%m-%d %H:%M:%S") if d["start"] else "brak danych",
            "Koniec": d["end"].strftime("%Y-%m-%d %H:%M:%S") if d["end"] else "brak danych",
            "Czas aktywności": d["duration"],
            "Długość (km)": round(d["distance"], 2),
            "Przewyższenie (m)": round(d["elev_diff"], 1),
        } for d in data])

        # DataFrame do pobrania (bez koloru)
        df_export = df.drop(columns=['Kolor'])
        # Przyciski obok siebie
        col_csv, col_excel, _ = st.columns([0.15, 0.15, 0.7])
        with col_csv:
            st.download_button(
                label="Pobierz tabelę jako CSV",
                data=df_export.to_csv(index=False).encode('utf-8'),
                file_name='podsumowanie_tras.csv',
                mime='text/csv'
            )
        with col_excel:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False)
            st.download_button(
                label="Pobierz tabelę jako Excel",
                data=excel_buffer.getvalue(),
                file_name='podsumowanie_tras.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

else:
    st.info("Wgraj pliki GPX, aby zobaczyć porównanie tras.")
