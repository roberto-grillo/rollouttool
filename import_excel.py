import pandas as pd
from models import db, Attivita
from main import app

# Percorso del file Excel nella root del progetto
EXCEL_PATH = "esempio.xlsx"


def importa_dati():
    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip()

    with app.app_context():
        for _, row in df.iterrows():
            # Gestione elegante e sicura della data
            value = row.get("DATA COLLAUDO SRB")
            data_parsed = pd.to_datetime(
                value, errors="coerce") if pd.notnull(value) else None
            data_collaudo_srb = data_parsed.date() if pd.notnull(
                data_parsed) else None

            nuova_attivita = Attivita(
                naming_bianchi=row.get("NAMING BIANCHI"),
                naming_grigi=row.get("NAMING GRIGI"),
                area=row.get("AREA"),
                regione=row.get("Regione"),
                provincia=row.get("Provincia"),
                comune_geografico=row.get("Comune geografico"),
                latitudine=row.get("Latitudine"),
                longitudine=row.get("Longitudine"),
                tipologia=row.get("Tipologia"),
                data_collaudo_srb=data_collaudo_srb,
                esito_collaudo=row.get("ESITO COLLAUDO"),
                pcn_cab_actual=row.get("PCN/CAB  actual 24/02/22"),
                pcn_cab_code_actual=row.get("PCN/CAB code actual 24/02/22"),
                soluzione_fwa=row.get("SOLUZIONE FWA"),
                attivita=row.get("ATTIVITA"),
                esito_bms=row.get("ESITO BMS"),
                ticket_bms=row.get("TICKET BMS"),
                zabbix=row.get("ZABBIX"),
                pni=row.get("PNI"),
                raggiungibilita=row.get("RAGGIUNGIBILITA'"),
                otdr=row.get("OTDR"),
                unims=row.get("UNIMS"),
                collaudo_nce=row.get(
                    "COLLAUDO NCE-FAN(EX N2510) O ONMSi(VIAVI)"),
                batterie=row.get("BATTERIE"),
                cablaggi_vs_rtu=row.get("CABLAGGI VS RTU"),
                mat=row.get("MAT"),
                comunicazione_mat_mtz=row.get("COMUNICAZIONE MAT VS MTZ"),
                documentazione_bh=row.get("DOCUMENTAZIONE BH"),
                note=row.get("NOTE"),
                categoria_pending=row.get("CATEGORIA PENDING"))
            db.session.add(nuova_attivita)

        db.session.commit()
        print("✅ Importazione completata!")


if __name__ == "__main__":
    importa_dati()
