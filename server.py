import socket
import threading
from datetime import datetime


# ========================================
# SERVER-EINSTELLUNGEN
# ========================================

HOST = "0.0.0.0"
PORT = 5000


# ========================================
# VERBUNDENE CLIENTS
# ========================================

clients = {}

clients_lock = threading.Lock()


# ========================================
# ZEITSTEMPEL
# ========================================

def zeit():

    return datetime.now().strftime("%H:%M")


# ========================================
# NACHRICHT AN CHAT SENDEN
# ========================================

def an_chat_senden(chat_code, nachricht):

    with clients_lock:

        teilnehmer = list(
            clients.get(chat_code, [])
        )

    for client, benutzername, ist_admin in teilnehmer:

        try:

            client.sendall(
                nachricht.encode("utf-8")
            )

        except Exception:

            pass


# ========================================
# ADMIN-BEFEHL AUSFÜHREN
# ========================================

def admin_kick(
    chat_code,
    admin_client,
    ziel_name
):

    with clients_lock:

        teilnehmer = clients.get(
            chat_code,
            []
        )

        ziel_client = None

        for client, benutzername, ist_admin in teilnehmer:

            if benutzername.lower() == ziel_name.lower():

                ziel_client = client
                break

    if ziel_client is None:

        admin_client.sendall(
            f"❌ Benutzer '{ziel_name}' wurde nicht gefunden.".encode(
                "utf-8"
            )
        )

        return

    if ziel_client == admin_client:

        admin_client.sendall(
            "❌ Du kannst dich nicht selbst kicken.".encode(
                "utf-8"
            )
        )

        return

    # ----------------------------------------
    # KICK-MELDUNG AN ALLE
    # ----------------------------------------

    an_chat_senden(
        chat_code,
        f"[{zeit()}] (🔴 {ziel_name} wurde vom Admin aus dem Chat entfernt)"
    )

    # ----------------------------------------
    # NACHRICHT AN GEKICKTEN CLIENT
    # ----------------------------------------

    try:

        ziel_client.sendall(
            "🔴 Du wurdest vom Admin aus dem Chat entfernt.".encode(
                "utf-8"
            )
        )

    except Exception:

        pass

    # ----------------------------------------
    # CLIENT AUS DER LISTE ENTFERNEN
    # ----------------------------------------

    with clients_lock:

        if chat_code in clients:

            clients[chat_code] = [
                eintrag
                for eintrag in clients[chat_code]
                if eintrag[0] != ziel_client
            ]

            if not clients[chat_code]:

                del clients[chat_code]

    # ----------------------------------------
    # SOCKET SCHLIESSEN
    # ----------------------------------------

    try:

        ziel_client.shutdown(
            socket.SHUT_RDWR
        )

    except Exception:

        pass

    try:

        ziel_client.close()

    except Exception:

        pass


# ========================================
# CLIENT VERARBEITEN
# ========================================

def client_verarbeiten(client, adresse):

    benutzername = None
    chat_code = None
    ist_admin = False
    wurde_gekickt = False

    print(
        f"🟢 Verbindung von "
        f"{adresse[0]}:{adresse[1]}"
    )

    try:

        # ----------------------------------------
        # BENUTZERDATEN EMPFANGEN
        # ----------------------------------------

        daten = client.recv(1024)

        if not daten:
            return

        daten = daten.decode("utf-8")

        teile = daten.split("|", 1)

        if len(teile) != 2:
            return

        benutzername = teile[0]
        chat_code = teile[1]

        # ----------------------------------------
        # ADMIN ERKENNEN
        # ----------------------------------------

        if benutzername.endswith(" 1942"):

            ist_admin = True

            benutzername = benutzername[:-5].strip()

        # ----------------------------------------
        # LEEREN NAMEN VERHINDERN
        # ----------------------------------------

        if not benutzername:

            client.sendall(
                "❌ Ungültiger Benutzername.".encode(
                    "utf-8"
                )
            )

            return

        # ----------------------------------------
        # CLIENT SPEICHERN
        # ----------------------------------------

        with clients_lock:

            if chat_code not in clients:

                clients[chat_code] = []

            clients[chat_code].append(
                (
                    client,
                    benutzername,
                    ist_admin
                )
            )

        print(
            f"[{zeit()}] 👤 {benutzername} ist "
            f"Chat {chat_code} beigetreten."
        )

        if ist_admin:

            print(
                f"[{zeit()}] 🛡️ {benutzername} ist Admin."
            )

        # ----------------------------------------
        # BEITRITTSMELDUNG
        # ----------------------------------------

        an_chat_senden(
            chat_code,
            f"[{zeit()}] (🟢 {benutzername} ist dem Chat beigetreten)"
        )

        # ----------------------------------------
        # NACHRICHTEN EMPFANGEN
        # ----------------------------------------

        while True:

            daten = client.recv(4096)

            if not daten:
                break

            nachricht = daten.decode(
                "utf-8"
            )

            # ----------------------------------------
            # ADMIN: /kick
            # ----------------------------------------

            if (
                ist_admin
                and nachricht.startswith("/kick ")
            ):

                ziel_name = nachricht[6:].strip()

                if ziel_name:

                    with clients_lock:

                        ziel_gefunden = False

                        for (
                            ziel_client,
                            ziel_benutzername,
                            ziel_admin
                        ) in clients.get(
                            chat_code,
                            []
                        ):

                            if (
                                ziel_benutzername.lower()
                                == ziel_name.lower()
                            ):

                                ziel_gefunden = True
                                break

                    if ziel_gefunden:

                        wurde_gekickt = True

                        admin_kick(
                            chat_code,
                            client,
                            ziel_name
                        )

                    else:

                        client.sendall(
                            f"❌ Benutzer '{ziel_name}' wurde nicht gefunden.".encode(
                                "utf-8"
                            )
                        )

                continue

            # ----------------------------------------
            # NORMALE CHAT-NACHRICHT
            # ----------------------------------------

            print(
                f"[{zeit()}] 💬 [{chat_code}] "
                f"{benutzername}: "
                f"{nachricht}"
            )

            an_chat_senden(
                chat_code,
                f"[{zeit()}] {benutzername}: {nachricht}"
            )

    except ConnectionResetError:

        pass

    except OSError as fehler:

        if getattr(fehler, "winerror", None) != 10038:

            print(
                f"⚠️ Fehler bei {adresse}: "
                f"{fehler}"
            )

    except Exception as fehler:

        print(
            f"⚠️ Fehler bei {adresse}: "
            f"{fehler}"
        )

    finally:

        # ----------------------------------------
        # CLIENT ENTFERNEN
        # ----------------------------------------

        with clients_lock:

            if chat_code in clients:

                clients[chat_code] = [
                    eintrag
                    for eintrag in clients[chat_code]
                    if eintrag[0] != client
                ]

                if not clients[chat_code]:

                    del clients[chat_code]

        # ----------------------------------------
        # NORMALES VERLASSEN
        # ----------------------------------------

        if (
            benutzername
            and chat_code
            and not wurde_gekickt
        ):

            print(
                f"[{zeit()}] 🔴 {benutzername} "
                f"hat den Chat verlassen."
            )

            an_chat_senden(
                chat_code,
                f"[{zeit()}] (🔴 {benutzername} hat den Chat verlassen)"
            )

        try:

            client.close()

        except Exception:

            pass


# ========================================
# SERVER STARTEN
# ========================================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind(
    (HOST, PORT)
)

server.listen()

print("========================================")
print("          💬 CMD MESSENGER")
print("             SERVER")
print("========================================")
print()

print("🟢 Server gestartet.")
print(f"🌐 Port: {PORT}")
print()
print("Warte auf Verbindungen...")
print()


# ========================================
# VERBINDUNGEN ANNEHMEN
# ========================================

while True:

    client, adresse = server.accept()

    thread = threading.Thread(
        target=client_verarbeiten,
        args=(client, adresse),
        daemon=True
    )

    thread.start()