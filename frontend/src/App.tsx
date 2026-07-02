import { useEffect, useRef, useState } from 'react'
import './App.css'
import { ApiFehler, berechnePackloesung, uploadSendung } from './api'
import { ErgebnisAnsicht } from './components/ErgebnisAnsicht'
import { UploadBereich } from './components/UploadBereich'
import { VorschauTabelle } from './components/VorschauTabelle'
import type { Artikel, Packergebnis, UploadFehlerEintrag } from './types'

type Schritt = 'upload' | 'vorschau' | 'berechnung' | 'ergebnis'

function App() {
  const [schritt, setSchritt] = useState<Schritt>('upload')
  const [artikel, setArtikel] = useState<Artikel[]>([])
  const [uploadWarnungen, setUploadWarnungen] = useState<string[]>([])
  const [uploadFehler, setUploadFehler] = useState<UploadFehlerEintrag[]>([])
  const [uploadLaeuft, setUploadLaeuft] = useState(false)
  const [ergebnis, setErgebnis] = useState<Packergebnis | null>(null)
  const [berechnungsFehler, setBerechnungsFehler] = useState<string | null>(null)
  const [dauertLange, setDauertLange] = useState(false)
  const langeTimer = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (langeTimer.current) window.clearTimeout(langeTimer.current)
    }
  }, [])

  const verarbeiteDatei = async (datei: File) => {
    setUploadLaeuft(true)
    setUploadFehler([])
    try {
      const antwort = await uploadSendung(datei)
      setArtikel(antwort.artikel)
      setUploadWarnungen(antwort.warnungen)
      setErgebnis(null)
      setSchritt('vorschau')
    } catch (fehler) {
      setUploadFehler(
        fehler instanceof ApiFehler
          ? fehler.fehler
          : [{ zeile: null, meldung: 'Unerwarteter Fehler beim Hochladen. Bitte erneut versuchen.' }],
      )
    } finally {
      setUploadLaeuft(false)
    }
  }

  const starteBerechnung = async () => {
    setSchritt('berechnung')
    setBerechnungsFehler(null)
    setDauertLange(false)
    // Ladeindikator-Stufe 2: Hinweis nach 10 Sekunden (SPEC 6.3)
    langeTimer.current = window.setTimeout(() => setDauertLange(true), 10_000)
    try {
      const antwort = await berechnePackloesung(artikel)
      setErgebnis(antwort)
      setSchritt('ergebnis')
    } catch (fehler) {
      setBerechnungsFehler(
        fehler instanceof ApiFehler
          ? fehler.message
          : 'Unerwarteter Fehler bei der Berechnung. Bitte erneut versuchen.',
      )
    } finally {
      if (langeTimer.current) window.clearTimeout(langeTimer.current)
      setDauertLange(false)
    }
  }

  const zuruecksetzen = () => {
    setSchritt('upload')
    setArtikel([])
    setUploadWarnungen([])
    setUploadFehler([])
    setErgebnis(null)
    setBerechnungsFehler(null)
  }

  return (
    <div className="app">
      <header className="app-kopf">
        <h1>Verpackungskonfigurator</h1>
        <p className="untertitel">
          Sendungsdatei hochladen → Artikel prüfen → kostenoptimierten Versandplan erhalten
        </p>
      </header>

      <main>
        {schritt === 'upload' && (
          <UploadBereich onDatei={verarbeiteDatei} fehler={uploadFehler} laeuft={uploadLaeuft} />
        )}

        {(schritt === 'vorschau' || schritt === 'berechnung') && (
          <>
            <VorschauTabelle artikel={artikel} warnungen={uploadWarnungen} />

            {schritt === 'vorschau' && (
              <div className="aktionen">
                <button className="sekundaer" onClick={zuruecksetzen}>
                  Andere Datei wählen
                </button>
                <button
                  className="primaer"
                  onClick={starteBerechnung}
                  disabled={artikel.length === 0}
                >
                  Versandplan berechnen
                </button>
              </div>
            )}

            {schritt === 'berechnung' && !berechnungsFehler && (
              <div className="lade-anzeige" role="status">
                <span className="spinner" aria-hidden />
                <p>Versandplan wird berechnet…</p>
                {dauertLange && (
                  <p className="lade-hinweis">
                    Die Berechnung dauert länger als üblich – bitte einen Moment Geduld. Nach 30
                    Sekunden wird automatisch abgebrochen.
                  </p>
                )}
              </div>
            )}

            {schritt === 'berechnung' && berechnungsFehler && (
              <div className="fehler-box" role="alert">
                <strong>Die Berechnung ist fehlgeschlagen:</strong>
                <p>{berechnungsFehler}</p>
                <div className="aktionen">
                  <button className="sekundaer" onClick={() => setSchritt('vorschau')}>
                    Zurück zur Vorschau
                  </button>
                  <button className="primaer" onClick={starteBerechnung}>
                    Erneut versuchen
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {schritt === 'ergebnis' && ergebnis && (
          <>
            <ErgebnisAnsicht ergebnis={ergebnis} artikel={artikel} />
            <div className="aktionen">
              <button className="sekundaer" onClick={() => setSchritt('vorschau')}>
                Zurück zur Artikelliste
              </button>
              <button className="primaer" onClick={zuruecksetzen}>
                Neue Sendung planen
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App
