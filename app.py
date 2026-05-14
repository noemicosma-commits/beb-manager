

import streamlit as st
from supabase import create_client
from datetime import date
from streamlit_calendar import calendar
import os 

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Gestionale B&B", layout="wide")
st.title("🏨 Gestionale B&B")

today = date.today()

rooms = supabase.table("rooms").select("*").execute().data
bookings = supabase.table("bookings").select("*").execute().data

# DASHBOARD
checkin_oggi = 0
checkout_oggi = 0
occupate_oggi = 0

for booking in bookings:
    ci = date.fromisoformat(booking["check_in"])
    co = date.fromisoformat(booking["check_out"])

    if ci == today:
        checkin_oggi += 1
    if co == today:
        checkout_oggi += 1
    if ci <= today < co:
        occupate_oggi += 1

libere_oggi = len(rooms) - occupate_oggi

c1, c2, c3, c4 = st.columns(4)
c1.metric("Check-in oggi", checkin_oggi)
c2.metric("Check-out oggi", checkout_oggi)
c3.metric("Camere occupate", occupate_oggi)
c4.metric("Camere libere", libere_oggi)

# CAMERE
st.divider()
st.subheader("🏠 Le mie camere")

camere_libere = []

for room in rooms:
    booking_attiva = None

    for booking in bookings:
        if booking["room_id"] == room["id"]:
            ci = date.fromisoformat(booking["check_in"])
            co = date.fromisoformat(booking["check_out"])

            if ci <= today < co:
                booking_attiva = booking
                break

    if booking_attiva:
        st.error(
            f"{room['name']} - OCCUPATA\n"
            f"Ospite: {booking_attiva['guest_name']}\n"
            f"Dal {booking_attiva['check_in']} al {booking_attiva['check_out']}"
        )
    else:
        st.success(f"{room['name']} - LIBERA")
        camere_libere.append(room)

# NUOVA PRENOTAZIONE
st.divider()
st.subheader("➕ Nuova prenotazione")

if camere_libere:
    camera = st.selectbox("Scegli camera", [r["name"] for r in camere_libere])
    ospite = st.text_input("Nome ospite")
    telefono = st.text_input("Telefono")
    check_in = st.date_input("Check-in")
    check_out = st.date_input("Check-out")
    amount = st.number_input("Importo totale (€)", min_value=0.0, step=10.0)
    paid = st.checkbox("Pagato")
    booking_source = st.checkbox("Prenotazione da Booking.com")
    notes = st.text_area("Note")

    if st.button("Prenota"):
        if not ospite:
            st.error("Inserisci nome ospite")
        elif check_out <= check_in:
            st.error("Il check-out deve essere dopo il check-in")
        else:
            selected_room = next(r for r in rooms if r["name"] == camera)
            fresh = supabase.table("bookings").select("*").execute().data

            conflitto = False

            for booking in fresh:
                if booking["room_id"] == selected_room["id"]:
                    es = date.fromisoformat(booking["check_in"])
                    ee = date.fromisoformat(booking["check_out"])

                    if check_in < ee and check_out > es:
                        conflitto = True
                        break

            if conflitto:
                st.error("⚠️ Questa camera è già prenotata in quelle date")
            else:
                supabase.table("bookings").insert({
                    "guest_name": ospite,
                    "phone": telefono,
                    "room_id": selected_room["id"],
                    "check_in": str(check_in),
                    "check_out": str(check_out),
                    "amount": amount,
                    "paid": paid,
                    "booking": booking_source,
                    "notes": notes
                }).execute()

                st.success("Prenotazione salvata!")
                st.rerun()
else:
    st.warning("Nessuna camera libera oggi")

# CALENDARIO
st.divider()
st.subheader("📅 Calendario prenotazioni")

events = []
booking_map = {}

for booking in bookings:
    room_name = next(
        room["name"]
        for room in rooms
        if room["id"] == booking["room_id"]
    )

    colore = "#2563eb" if booking.get("booking") else "#16a34a"

    titolo = f"{booking['guest_name']} — {room_name}"

    booking_map[titolo] = booking

    events.append({
        "title": titolo,
        "start": str(booking["check_in"]),
        "end": str(booking["check_out"]),
        "backgroundColor": colore,
        "borderColor": colore
    })

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek"
    }
}

calendar(events=events, options=calendar_options)

st.subheader("📋 Dettagli prenotazione")

if booking_map:
    selected_title = st.selectbox(
        "Seleziona prenotazione",
        list(booking_map.keys()),
        key="calendar_booking_select"
    )

    selected_booking = booking_map[selected_title]

    room_name = next(
        room["name"]
        for room in rooms
        if room["id"] == selected_booking["room_id"]
    )

    st.info(
        f"Nome: {selected_booking['guest_name']}\n"
        f"Camera: {room_name}\n"
        f"Telefono: {selected_booking.get('phone', '-')}\n"
        f"Check-in: {selected_booking['check_in']}\n"
        f"Check-out: {selected_booking['check_out']}\n"
        f"Importo: €{selected_booking.get('amount', 0)}\n"
        f"Pagato: {'Sì' if selected_booking.get('paid') else 'No'}\n"
        f"Booking.com: {'Sì' if selected_booking.get('booking') else 'No'}\n"
        f"Note: {selected_booking.get('notes', '-')}"
    )

# GESTIONE PRENOTAZIONI
st.divider()
st.subheader("🔍 Gestione prenotazioni")

nome_ricerca = st.text_input("Cerca ospite", key="ricerca_ospite")

if nome_ricerca:
    fresh_search = supabase.table("bookings").select("*").execute().data

    risultati = [
        b for b in fresh_search
        if nome_ricerca.lower() in b["guest_name"].lower()
    ]

    if risultati:
        for booking in risultati:
            room_name = next(
                room["name"]
                for room in rooms
                if room["id"] == booking["room_id"]
            )

            with st.expander(f"{booking['guest_name']} — {room_name}"):
                nuovo_nome = st.text_input(
                    "Nome ospite",
                    booking["guest_name"],
                    key=f"nome_{booking['id']}"
                )

                nuovo_telefono = st.text_input(
                    "Telefono",
                    booking.get("phone") or "",
                    key=f"phone_{booking['id']}"
                )

                nuovo_checkin = st.date_input(
                    "Check-in",
                    date.fromisoformat(booking["check_in"]),
                    key=f"ci_{booking['id']}"
                )

                nuovo_checkout = st.date_input(
                    "Check-out",
                    date.fromisoformat(booking["check_out"]),
                    key=f"co_{booking['id']}"
                )

                nuovo_amount = st.number_input(
                    "Importo totale (€)",
                    min_value=0.0,
                    value=float(booking.get("amount") or 0),
                    key=f"amt_{booking['id']}"
                )

                nuovo_paid = st.checkbox(
                    "Pagato",
                    value=bool(booking.get("paid")),
                    key=f"paid_{booking['id']}"
                )

                nuovo_booking = st.checkbox(
                    "Prenotazione da Booking.com",
                    value=bool(booking.get("booking")),
                    key=f"book_{booking['id']}"
                )

                nuove_note = st.text_area(
                    "Note",
                    booking.get("notes") or "",
                    key=f"notes_{booking['id']}"
                )

                if st.button("💾 Salva modifiche", key=f"save_{booking['id']}"):
                    supabase.table("bookings").update({
                        "guest_name": nuovo_nome,
                        "phone": nuovo_telefono,
                        "check_in": str(nuovo_checkin),
                        "check_out": str(nuovo_checkout),
                        "amount": nuovo_amount,
                        "paid": nuovo_paid,
                        "booking": nuovo_booking,
                        "notes": nuove_note
                    }).eq("id", booking["id"]).execute()

                    st.success("Prenotazione aggiornata")
                    st.rerun()

                if st.button("❌ Cancella prenotazione", key=f"delete_{booking['id']}"):
                    supabase.table("bookings").delete().eq("id", booking["id"]).execute()
                    st.success("Prenotazione cancellata")
                    st.rerun()
    else:
        st.warning("Nessuna prenotazione trovata")

# DISPONIBILITÀ
st.divider()
st.subheader("📅 Controlla disponibilità")

arrivo = st.date_input("Data arrivo", key="arrivo_check")
partenza = st.date_input("Data partenza", key="partenza_check")

if st.button("Controlla disponibilità"):
    if partenza <= arrivo:
        st.error("Date non valide")
    else:
        disponibili = []

        for room in rooms:
            occupata = False

            for booking in bookings:
                if booking["room_id"] == room["id"]:
                    es = date.fromisoformat(booking["check_in"])
                    ee = date.fromisoformat(booking["check_out"])

                    if arrivo < ee and partenza > es:
                        occupata = True
                        break

            if not occupata:
                disponibili.append(room["name"])

        if disponibili:
            st.success("Camere disponibili:")
            for nome in disponibili:
                st.write(nome)
        else:
            st.error("Nessuna camera disponibile")
