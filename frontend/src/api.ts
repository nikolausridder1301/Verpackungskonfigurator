import type { Artikel, Packergebnis, UploadAntwort, UploadFehlerEintrag } from './types'

export const API_BASE = 'http://localhost:8000'

/** Fehler mit nutzerverständlichen, ggf. zeilenbezogenen Meldungen. */
export class ApiFehler extends Error {
  fehler: UploadFehlerEintrag[]

  constructor(fehler: UploadFehlerEintrag[]) {
    super(fehler.map((f) => f.meldung).join(' '))
    this.fehler = fehler
  }
}

const VERBINDUNGS_FEHLER: UploadFehlerEintrag[] = [
  {
    zeile: null,
    meldung:
      'Das Backend ist nicht erreichbar. Bitte prüfen, ob die Anwendung läuft, und erneut versuchen.',
  },
]

async function alsApiFehler(response: Response): Promise<ApiFehler> {
  try {
    const daten = await response.json()
    if (daten?.detail?.fehler) return new ApiFehler(daten.detail.fehler)
    if (daten?.detail?.meldung) return new ApiFehler([{ zeile: null, meldung: daten.detail.meldung }])
  } catch {
    // Antwort war kein JSON -> generische Meldung unten
  }
  return new ApiFehler([
    { zeile: null, meldung: 'Bei der Verarbeitung ist ein unerwarteter Fehler aufgetreten. Bitte erneut versuchen.' },
  ])
}

export async function uploadSendung(datei: File): Promise<UploadAntwort> {
  const formData = new FormData()
  formData.append('datei', datei)
  let response: Response
  try {
    response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
  } catch {
    throw new ApiFehler(VERBINDUNGS_FEHLER)
  }
  if (!response.ok) throw await alsApiFehler(response)
  return response.json()
}

export async function berechnePackloesung(artikel: Artikel[]): Promise<Packergebnis> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/calculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artikel }),
    })
  } catch {
    throw new ApiFehler(VERBINDUNGS_FEHLER)
  }
  if (!response.ok) throw await alsApiFehler(response)
  return response.json()
}
