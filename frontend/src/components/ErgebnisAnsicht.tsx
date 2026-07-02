import type { Artikel, Packergebnis } from '../types'
import { farbZuordnung } from '../farben'
import { PackeinheitKarte } from './PackeinheitKarte'

interface Props {
  ergebnis: Packergebnis
  artikel: Artikel[]
}

/** Ergebnisübersicht, Warnbanner und Verpackungskarten (Issues #21, #24, #25). */
export function ErgebnisAnsicht({ ergebnis, artikel }: Props) {
  const farben = farbZuordnung(artikel)
  const einheitenGesamt = ergebnis.einheiten.length

  return (
    <section className="ergebnis">
      {!ergebnis.stabil && (
        <div className="stabilitaets-banner" role="alert">
          <strong>⚠️ Stabilität nicht garantiert – manuelle Prüfung erforderlich.</strong>
          <ul>
            {ergebnis.warnungen.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="uebersicht-karten">
        <div className="kennzahl">
          <span className="kennzahl-wert">
            {ergebnis.gesamtkosten_eur.toFixed(2).replace('.', ',')} €
          </span>
          <span className="kennzahl-label">Gesamtkosten Verpackung</span>
        </div>
        <div className="kennzahl">
          <span className="kennzahl-wert">{ergebnis.gesamtgewicht_kg.toLocaleString('de-DE')} kg</span>
          <span className="kennzahl-label">Gesamtgewicht (inkl. Verpackung)</span>
        </div>
        <div className="kennzahl">
          <span className="kennzahl-wert">{einheitenGesamt}</span>
          <span className="kennzahl-label">
            Verpackungseinheit{einheitenGesamt === 1 ? '' : 'en'} (
            {Object.entries(ergebnis.anzahl_je_typ)
              .map(([id, anzahl]) => `${anzahl}× ${id}`)
              .join(', ')}
            )
          </span>
        </div>
      </div>

      {ergebnis.hinweise.length > 0 && (
        <div className="warn-box" role="status">
          {ergebnis.hinweise.map((h, i) => (
            <p key={i}>{h}</p>
          ))}
        </div>
      )}

      <div className="legende">
        {artikel.map((a) => (
          <span key={a.artikel_id} className="legende-eintrag">
            <span className="farb-punkt" style={{ background: farben.get(a.artikel_id) }} />
            {a.artikel_id} – {a.bezeichnung}
            {a.zerbrechlich ? ' (zerbrechlich, schraffiert)' : ''}
          </span>
        ))}
      </div>

      <div className="karten-raster">
        {ergebnis.einheiten.map((einheit, i) => (
          <PackeinheitKarte key={i} einheit={einheit} farben={farben} />
        ))}
      </div>
    </section>
  )
}
