import type { Artikel } from '../types'
import { farbZuordnung } from '../farben'

interface Props {
  artikel: Artikel[]
  warnungen: string[]
}

/** Artikel-Vorschau vor der Berechnung (Issue #20). */
export function VorschauTabelle({ artikel, warnungen }: Props) {
  const farben = farbZuordnung(artikel)
  const gesamtStueck = artikel.reduce((summe, a) => summe + a.menge, 0)

  return (
    <section className="vorschau">
      <h2>Eingelesene Artikel</h2>
      {warnungen.length > 0 && (
        <div className="warn-box" role="status">
          {warnungen.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
      <div className="tabelle-wrapper">
        <table>
          <thead>
            <tr>
              <th>Artikel-ID</th>
              <th>Bezeichnung</th>
              <th>Länge (mm)</th>
              <th>Breite (mm)</th>
              <th>Höhe (mm)</th>
              <th>Gewicht (kg)</th>
              <th>Menge</th>
              <th>Zerbrechlich</th>
            </tr>
          </thead>
          <tbody>
            {artikel.map((a) => (
              <tr key={a.artikel_id}>
                <td>
                  <span className="farb-punkt" style={{ background: farben.get(a.artikel_id) }} />
                  {a.artikel_id}
                </td>
                <td>{a.bezeichnung}</td>
                <td className="zahl">{a.laenge_mm}</td>
                <td className="zahl">{a.breite_mm}</td>
                <td className="zahl">{a.hoehe_mm}</td>
                <td className="zahl">{a.gewicht_kg}</td>
                <td className="zahl">{a.menge}</td>
                <td>{a.zerbrechlich ? '⚠️ ja' : 'nein'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="vorschau-summe">
        {artikel.length} Artikeltyp{artikel.length === 1 ? '' : 'en'}, {gesamtStueck} Stück gesamt
      </p>
    </section>
  )
}
