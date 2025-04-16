import os
import pandas as pd
from flask import Flask, redirect, request, session, url_for, render_template, flash
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
from sqlalchemy import and_, DateTime, Date, Integer, Float, Numeric, REAL
from datetime import datetime, date
from models import db, Attivita  # importa db centralizzato

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Cartella per le immagini
UPLOAD_FOLDER = os.path.abspath(os.path.join('static', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attivita.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# OAuth config\CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTH_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
SCOPE = ["openid", "email", "profile", "User.Read"]

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
    attivita = Attivita() if attivita_id == 0 else Attivita.query.get_or_404(attivita_id)

    for column in attivita.__table__.columns:
        nome_colonna = column.name
        if nome_colonna != "id" and nome_colonna in request.form:
            nuovo_valore = request.form[nome_colonna].strip()

            if nuovo_valore == "":
                setattr(attivita, nome_colonna, None)
            else:
                tipo = column.type

                if isinstance(tipo, DateTime):
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                        try:
                            valore = datetime.strptime(nuovo_valore, fmt)
                            setattr(attivita, nome_colonna, valore)
                            break
                        except ValueError:
                            continue

                elif isinstance(tipo, Date):
                    try:
                        valore = datetime.strptime(nuovo_valore, "%Y-%m-%d").date()
                        setattr(attivita, nome_colonna, valore)
                    except ValueError:
                        pass

                elif isinstance(tipo, (Integer, Float, Numeric, REAL)):
                    try:
                        setattr(attivita, nome_colonna, float(nuovo_valore))
                    except ValueError:
                        setattr(attivita, nome_colonna, None)

                else:
                    setattr(attivita, nome_colonna, nuovo_valore)

    if attivita_id == 0:
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

    try:
        df = pd.read_excel(file)
        for _, row in df[df['naming_bianchi'].notna()].iterrows():
            attivita = Attivita()
            for col in row.index:
                if hasattr(attivita, col):
                    value = row[col]
                    if pd.isna(value):
                        setattr(attivita, col, None)
                    elif isinstance(getattr(Attivita, col).property.columns[0].type, DateTime):
                        setattr(attivita, col, pd.to_datetime(value).to_pydatetime())
                    elif isinstance(getattr(Attivita, col).property.columns[0].type, Date):
                        setattr(attivita, col, pd.to_datetime(value).date())
                    else:
                        setattr(attivita, col, value)
            db.session.add(attivita)
        db.session.commit()
        flash("Importazione completata con successo.")
    except Exception as e:
        flash(f"Errore durante l'importazione: {e}")

    return redirect(url_for("elenco_attivita"))






if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)
