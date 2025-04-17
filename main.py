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
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

with app.app_context():
    db.create_all()

# OAuth config\
oauth = OAuth2Session(Config.CLIENT_ID, scope=Config.SCOPE, redirect_uri=Config.REDIRECT_URI)

@app.route("/")
def index():
    if "user" in session:
        return f"<h3>Sei loggato come: {session['user']['name']} ({session['user']['email']})</h3><a href='/attivita'>Vai alla lista</a><br><a href='/logout'>Logout</a>"
    return "<a href='/login'>Login con Microsoft</a>"

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

    for column in attivita.__table__.columns:
        nome_colonna = column.name
        if nome_colonna != "id" and nome_colonna in request.form:
            nuovo_valore = request.form[nome_colonna].strip()
            valore_vecchio = getattr(attivita, nome_colonna)

            if nuovo_valore == "":
                valore_nuovo = None
            else:
                tipo = column.type
                try:
                    if isinstance(tipo, DateTime):
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                            try:
                                valore_nuovo = datetime.strptime(nuovo_valore, fmt)
                                break
                            except ValueError:
                                continue
                    elif isinstance(tipo, Date):
                        valore_nuovo = datetime.strptime(nuovo_valore, "%Y-%m-%d").date()
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
            attivita.data_inserimento = datetime.now()

            for col_name in df.columns:
                if hasattr(attivita, col_name):
                    value = row[col_name]
                    if pd.isna(value):
                        setattr(attivita, col_name, None)
                    else:
                        tipo = getattr(Attivita, col_name).property.columns[0].type
                        if isinstance(tipo, DateTime):
                            setattr(attivita, col_name, pd.to_datetime(value).to_pydatetime())
                        elif isinstance(tipo, Date):
                            setattr(attivita, col_name, pd.to_datetime(value).date())
                        elif isinstance(tipo, (Integer, Float, Numeric, REAL)):
                            try:
                                setattr(attivita, col_name, float(value))
                            except ValueError:
                                setattr(attivita, col_name, None)
                        else:
                            setattr(attivita, col_name, str(value))

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



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)
