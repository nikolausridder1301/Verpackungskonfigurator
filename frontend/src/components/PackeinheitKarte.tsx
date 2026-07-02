import { useState } from 'react'
import type { Packeinheit, Platzierung } from '../types'

interface Props {
  einheit: Packeinheit
  farben: Map<string, string>
}

interface TooltipDaten {
  platzierung: Platzierung
  x: number
  y: number
}

const NAMEN: Record<string, string> = { karton: 'Karton', palette: 'Palette' }

/** Kachel je Verpackungseinheit: Draufsicht je Lage + Seitenansicht (Issues #22, #23, #36). */
export function PackeinheitKarte({ einheit, farben }: Props) {
  const [tooltip, setTooltip] = useState<TooltipDaten | null>(null)

  const zeigeTooltip = (p: Platzierung) => (e: React.MouseEvent) => {
    setTooltip({ platzierung: p, x: e.clientX, y: e.clientY })
  }

  const artikelRect = (
    p: Platzierung,
    i: number,
    x: number,
    y: number,
    breite: number,
    hoehe: number,
  ) => (
    <g key={i}>
      <rect
        x={x}
        y={y}
        width={breite}
        height={hoehe}
        fill={farben.get(p.artikel_id) ?? '#888'}
        stroke="#1e293b"
        strokeWidth={Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 250}
        onMouseMove={zeigeTooltip(p)}
        onMouseLeave={() => setTooltip(null)}
        onClick={zeigeTooltip(p)}
      />
      {p.zerbrechlich && (
        <rect
          x={x}
          y={y}
          width={breite}
          height={hoehe}
          fill="url(#zerbrechlich-muster)"
          pointerEvents="none"
        />
      )}
    </g>
  )

  return (
    <article className="einheit-karte">
      <header className="einheit-kopf">
        <h3>
          {NAMEN[einheit.typ] ?? einheit.typ} „{einheit.verpackung_id}“ Nr. {einheit.nummer}
        </h3>
        <span className="einheit-fakten">
          {einheit.kosten_eur.toFixed(2).replace('.', ',')} € · {einheit.gewicht_kg.toLocaleString('de-DE')} kg ·{' '}
          {einheit.auslastung_prozent.toLocaleString('de-DE')} % befüllt
        </span>
      </header>

      {einheit.warnungen.length > 0 && (
        <div className="warn-box klein" role="alert">
          {einheit.warnungen.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden>
        <defs>
          <pattern
            id="zerbrechlich-muster"
            patternUnits="userSpaceOnUse"
            width="14"
            height="14"
            patternTransform="rotate(45)"
          >
            <line x1="0" y1="0" x2="0" y2="14" stroke="rgba(255,255,255,0.85)" strokeWidth="4" />
          </pattern>
        </defs>
      </svg>

      <div className="ansichten">
        <div className="ansicht-gruppe">
          <h4>Draufsicht je Lage</h4>
          <div className="lagen-reihe">
            {einheit.lagen.map((lage) => (
              <figure key={lage.index} className="lage-figur">
                <svg
                  viewBox={`-2 -2 ${einheit.basis_laenge_mm + 4} ${einheit.basis_breite_mm + 4}`}
                  className="plan-svg"
                  role="img"
                  aria-label={`Draufsicht Lage ${lage.index + 1}`}
                >
                  <rect
                    x={0}
                    y={0}
                    width={einheit.basis_laenge_mm}
                    height={einheit.basis_breite_mm}
                    className="verpackung-umriss"
                  />
                  {einheit.platzierungen
                    .filter((p) => p.lage_index === lage.index)
                    .map((p, i) => artikelRect(p, i, p.x_mm, p.y_mm, p.laenge_mm, p.breite_mm))}
                </svg>
                <figcaption>
                  Lage {lage.index + 1}
                  {lage.index === 0 ? ' (unten)' : ''}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>

        <div className="ansicht-gruppe">
          <h4>Seitenansicht</h4>
          <figure className="lage-figur">
            <svg
              viewBox={`-2 -2 ${einheit.basis_laenge_mm + 4} ${einheit.max_hoehe_mm + 4}`}
              className="plan-svg seitenansicht"
              role="img"
              aria-label="Seitenansicht mit Schwerpunkt"
            >
              <rect
                x={0}
                y={0}
                width={einheit.basis_laenge_mm}
                height={einheit.max_hoehe_mm}
                className="verpackung-umriss"
              />
              {[...einheit.platzierungen]
                .sort((a, b) => b.y_mm - a.y_mm)
                .map((p, i) =>
                  artikelRect(
                    p,
                    i,
                    p.x_mm,
                    einheit.max_hoehe_mm - p.z_mm - p.hoehe_mm,
                    p.laenge_mm,
                    p.hoehe_mm,
                  ),
                )}
              {/* Schwerpunkt-Markierung (Issue #23) */}
              <g
                className="schwerpunkt-marker"
                transform={`translate(${einheit.schwerpunkt.x_mm}, ${
                  einheit.max_hoehe_mm - einheit.schwerpunkt.z_mm
                })`}
              >
                <circle r={Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 40} />
                <line
                  x1={-Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 25}
                  x2={Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 25}
                  y1={0}
                  y2={0}
                />
                <line
                  y1={-Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 25}
                  y2={Math.max(einheit.basis_laenge_mm, einheit.max_hoehe_mm) / 25}
                  x1={0}
                  x2={0}
                />
              </g>
            </svg>
            <figcaption>⌖ = Schwerpunkt</figcaption>
          </figure>
        </div>
      </div>

      <p className="einheit-masse">
        Innenmaße: {einheit.basis_laenge_mm.toLocaleString('de-DE')} ×{' '}
        {einheit.basis_breite_mm.toLocaleString('de-DE')} × {einheit.max_hoehe_mm.toLocaleString('de-DE')} mm
      </p>

      {tooltip && (
        <div
          className="tooltip"
          style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
          onClick={() => setTooltip(null)}
        >
          <strong>{tooltip.platzierung.artikel_id}</strong> – {tooltip.platzierung.bezeichnung}
          <br />
          {tooltip.platzierung.laenge_mm} × {tooltip.platzierung.breite_mm} ×{' '}
          {tooltip.platzierung.hoehe_mm} mm
          <br />
          {tooltip.platzierung.gewicht_kg.toLocaleString('de-DE')} kg
          {tooltip.platzierung.zerbrechlich ? ' · zerbrechlich' : ''}
          <br />
          <em>Lage {tooltip.platzierung.lage_index + 1}</em>
        </div>
      )}
    </article>
  )
}
