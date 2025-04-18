from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()  # unica istanza condivisa


def current_time_truncated():
    return datetime.now().replace(microsecond=0)


class Attivita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_inserimento = db.Column(db.DateTime, default=current_time_truncated)
    naming_bianchi = db.Column(db.String(100), nullable=False)
    naming_grigi = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(50))
    regione = db.Column(db.String(50))
    provincia = db.Column(db.String(50))
    comune_geografico = db.Column(db.String(100))
    tipologia = db.Column(db.String(50))
    latitudine = db.Column(db.Float)
    longitudine = db.Column(db.Float)

    data_collaudo_srb = db.Column(db.Date)
    esito_collaudo = db.Column(db.String(10))  # OK / NOK / vuoto

    pcn_cab = db.Column(db.String(100))
    pcn_cab_code = db.Column(db.String(100))
    soluzione_fwa = db.Column(db.String(50))
    attivita = db.Column(db.String(20))  # Swap / Integrazione / vuoto

    esito_bms = db.Column(db.String(10))
    ticket_bms = db.Column(db.String(100))
    zabbix = db.Column(db.String(100))
    pni = db.Column(db.String(100))
    raggiungibilita = db.Column(db.String(100))
    otdr = db.Column(db.String(100))
    unims = db.Column(db.String(100))
    collaudo_nce_fan_onmsi = db.Column(db.String(100))
    batterie = db.Column(db.String(100))
    cablaggi_vs_rtu = db.Column(db.String(100))
    mat = db.Column(db.String(100))
    comunicazione_mat_vs_mtz = db.Column(db.String(100))
    documentazione_bh = db.Column(db.String(100))
    note = db.Column(db.Text)
    categoria_pending = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=current_time_truncated)




class StoricoModifiche(db.Model):
    __tablename__ = 'storico_modifiche'

    id = db.Column(db.Integer, primary_key=True)
    attivita_id = db.Column(db.Integer, nullable=False)
    campo = db.Column(db.String(100), nullable=False)
    valore_precedente = db.Column(db.Text)
    valore_nuovo = db.Column(db.Text)
    data_modifica = db.Column(db.DateTime, default=datetime.utcnow)  # gestito automaticamente
    utente = db.Column(db.String(255))  # es. "utente@example.com"
