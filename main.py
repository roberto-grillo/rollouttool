import os
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from flask import Flask, redirect, request, session, url_for, render_template, flash
from requests_oauthlib import OAuth2Session
from sqlalchemy import and_, DateTime, Date, Integer, Float, Numeric, REAL
from datetime import datetime, date
from models import db, Attivita  # importa db centralizzato
from config import Config


app = Flask(__name__)
app.config.from_object(Config)

# DEBUG: stampa il database in uso
print("🔧 DEBUG - Configurazione attiva:")
print("📁 UPLOAD_FOLDER:", app.config["UPLOAD_FOLDER"])
print("🔐 SECRET_KEY presente:", bool(app.config["SECRET_KEY"]))
print("🔁 Ambiente:", os.getenv("FLASK_ENV", "production"))
print("🖥️ Locale:", os.uname().nodename if hasattr(os, "uname") else "n/a")
##

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

with app.app_context():
    db.create_all()

# OAuth config\
oauth = OAuth2Session(Config.CLIENT_ID, scope=Config.SCOPE, redirect_uri=Config.REDIRECT_URI)

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("elenco_attivita"))
    return render_template("login.html")


@app.route("/login")
def login():
    oauth = OAuth2Session(CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = oauth.authorization_url(AUTH_URL)
    session["oauth_state"] = state
    return redirect(authorization_url)

@app.route("/auth/callback")
def callback():
    oauth = OAuth2Session(CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    token = oauth.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
    userinfo = oauth.get("https://graph.microsoft.com/v1.0/me").json()
    session["user"] = {
        "name": userinfo.get("displayName", "Sconosciuto"),
        "email": userinfo.get("userPrincipalName", "N/A")
    }
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/attivita")
def elenco_attivita():
    attivita = Attivita.query.all()
    return render_template("attivita.html", attivita=attivita)

@app.route("/attivita/0")
def nuova_attivita():
    attivita_vuota = Attivita()
    attivita_vuota.id = 0
    return render_template("dettaglio_attivita.html", attivita=attivita_vuota, immagini=[], getattr=getattr)

@app.route("/attivita/<int:attivita_id>")
def dettaglio_attivita(attivita_id):
    attivita = Attivita.query.get_or_404(attivita_id)
    folder = os.path.join(app.config['UPLOAD_FOLDER'], str(attivita_id))
    immagini = []
    if os.path.exists(folder):
        immagini = [
            f for f in os.listdir(folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
        ]
    return render_template("dettaglio_attivita.html",
                           attivita=attivita,
                           immagini=immagini,
                           getattr=getattr)

@app.route("/attivita/<int:attivita_id>/modifica", methods=["POST"])
def modifica_attivita(attivita_id):
    from models import StoricoModifiche  # importa solo se non lo hai già fatto

    attivita = Attivita() if attivita_id == 0 else Attivita.query.get_or_404(attivita_id)
    is_nuova = attivita_id == 0
    if is_nuova:
        attivita.data_inserimento = datetime.now().replace(microsecond=0)


    for column in attivita.__table__.columns:
        nome_colonna = column.name
        if nome_colonna != "id" and nome_colonna in request.form:
            nuovo_valore = request.form[nome_colonna].strip()
            valore_vecchio = getattr(attivita, nome_colonna)

            tipo = column.type
            valore_nuovo = None
            try:
                if nuovo_valore == "":
                    if isinstance(tipo, (DateTime, Date, Integer, Float, Numeric, REAL)):
                        valore_nuovo = None
                    else:
                        valore_nuovo = ""  # stringa vuota al posto di None
                else:
                    if isinstance(tipo, DateTime):
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                            try:
                                valore_nuovo = datetime.strptime(nuovo_valore, fmt)
                                break
                            except ValueError:
                                continue
                                
                    elif isinstance(tipo, Date):
                        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                            try:
                                valore_nuovo = datetime.strptime(nuovo_valore, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            valore_nuovo = None # se nessun formato combacia
                            
                        
                    elif isinstance(tipo, (Integer, Float, Numeric, REAL)):
                        valore_nuovo = float(nuovo_valore)
                    else:
                        valore_nuovo = nuovo_valore
            except Exception:
                valore_nuovo = None


            if not is_nuova and valore_nuovo != valore_vecchio:
                storico = StoricoModifiche(
                    attivita_id=attivita.id,
                    campo=nome_colonna,
                    valore_precedente=str(valore_vecchio),
                    valore_nuovo=str(valore_nuovo),
                    utente=session.get("user", {}).get("email", "ignoto")
                )
                db.session.add(storico)

            setattr(attivita, nome_colonna, valore_nuovo)

    if is_nuova:
        db.session.add(attivita)

    db.session.commit()
    return redirect(url_for("dettaglio_attivita", attivita_id=attivita.id))


@app.route("/attivita/<int:attivita_id>/upload_foto", methods=["POST"])
def upload_foto(attivita_id):
    foto = request.files.get("foto")
    if foto and foto.filename:
        folder = os.path.join(app.config['UPLOAD_FOLDER'], str(attivita_id))
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, foto.filename)
        foto.save(filepath)
    return redirect(url_for('dettaglio_attivita', attivita_id=attivita_id))

@app.route("/attivita/<int:attivita_id>/elimina")
def elimina_attivita(attivita_id):
    attivita = Attivita.query.get_or_404(attivita_id)
    db.session.delete(attivita)
    db.session.commit()
    return redirect(url_for("elenco_attivita"))

@app.route("/mappa")
def mappa():
    attivita_con_coordinate = Attivita.query.filter(
        and_(Attivita.latitudine.isnot(None),
             Attivita.longitudine.isnot(None))).all()

    attivita_json = [{
        "id": a.id,
        "naming_bianchi": a.naming_bianchi,
        "regione": a.regione,
        "tipologia": a.tipologia,
        "latitudine": a.latitudine,
        "longitudine": a.longitudine,
        "esito": a.esito_collaudo
    } for a in attivita_con_coordinate]

    return render_template("mappa.html", attivita_json=attivita_json)

# Inizializza il database al primo avvio
with app.app_context():
    db.create_all()




@app.route("/importa_excel", methods=["POST"])
def importa_excel():
    file = request.files.get("file")
    if not file:
        flash("Nessun file selezionato.")
        return redirect(url_for("elenco_attivita"))

    # ⛔ Verifica la dimensione del file in MB
    file.seek(0, os.SEEK_END)
    file_length_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if file_length_mb > app.config["MAX_UPLOAD_SIZE_MB"]:
        flash(f"Il file supera il limite di {app.config['MAX_UPLOAD_SIZE_MB']} MB.")
        return redirect(url_for("elenco_attivita"))

    try:
        df = pd.read_excel(file)

        # Normalizza i nomi delle colonne
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        for _, row in df.iterrows():
            if pd.isna(row.get("naming_bianchi")) or pd.isna(row.get("naming_grigi")):
                continue  # salta righe incomplete

            attivita = Attivita()
            attivita.data_inserimento = datetime.now().replace(microsecond=0)

            for col_name in df.columns:
                if hasattr(attivita, col_name):
                    value = row[col_name]
                    tipo = getattr(Attivita, col_name).property.columns[0].type
                    try:
                        if pd.isna(value):
                            if isinstance(tipo, (DateTime, Date, Integer, Float, Numeric, REAL)):
                                setattr(attivita, col_name, None)
                            else:
                                setattr(attivita, col_name, "")
                        else:
                            if isinstance(tipo, DateTime):
                                dt = pd.to_datetime(value).to_pydatetime().replace(microsecond=0)
                                setattr(attivita, col_name, dt)
                            elif isinstance(tipo, Date):
                                setattr(attivita, col_name, pd.to_datetime(value).date())
                            elif isinstance(tipo, (Integer, Float, Numeric, REAL)):
                                setattr(attivita, col_name, float(value))
                            else:
                                setattr(attivita, col_name, str(value))
                    except Exception:
                        setattr(attivita, col_name, None)

            db.session.add(attivita)

        db.session.commit()
        flash("Importazione completata con successo.")
    except Exception as e:
        flash(f"Errore durante l'importazione: {e}")

    return redirect(url_for("elenco_attivita"))



@app.route("/storico/<int:attivita_id>")
def storico_modifiche(attivita_id):
    from models import StoricoModifiche  # se non è già importato in alto

    modifiche = StoricoModifiche.query.filter_by(attivita_id=attivita_id).order_by(
        StoricoModifiche.data_modifica.desc()
    ).all()

    return render_template("storico.html", modifiche=modifiche, attivita_id=attivita_id)

@app.route("/impostazioni")
def impostazioni():
    return render_template("impostazioni.html")

@app.route("/reset_db", methods=["POST"])
def reset_db():
    from models import Attivita, StoricoModifiche
    db.session.query(StoricoModifiche).delete()
    db.session.query(Attivita).delete()
    db.session.commit()
    flash("Tutte le attività e lo storico modifiche sono stati eliminati.")
    return redirect(url_for("elenco_attivita"))





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)
