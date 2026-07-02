export interface Artikel {
  artikel_id: string
  bezeichnung: string
  laenge_mm: number
  breite_mm: number
  hoehe_mm: number
  gewicht_kg: number
  menge: number
  zerbrechlich: boolean
}

export interface UploadAntwort {
  artikel: Artikel[]
  warnungen: string[]
}

export interface UploadFehlerEintrag {
  zeile: number | null
  meldung: string
}

export interface Platzierung {
  artikel_id: string
  bezeichnung: string
  x_mm: number
  y_mm: number
  z_mm: number
  laenge_mm: number
  breite_mm: number
  hoehe_mm: number
  lage_index: number
  gewicht_kg: number
  zerbrechlich: boolean
}

export interface Lage {
  index: number
  z_mm: number
  hoehe_mm: number
}

export interface Schwerpunkt {
  x_mm: number
  y_mm: number
  z_mm: number
}

export interface Packeinheit {
  verpackung_id: string
  typ: string
  nummer: number
  basis_laenge_mm: number
  basis_breite_mm: number
  max_hoehe_mm: number
  kosten_eur: number
  gewicht_kg: number
  zuladung_kg: number
  auslastung_prozent: number
  schwerpunkt: Schwerpunkt
  lagen: Lage[]
  platzierungen: Platzierung[]
  warnungen: string[]
}

export interface Packergebnis {
  einheiten: Packeinheit[]
  anzahl_je_typ: Record<string, number>
  gesamtkosten_eur: number
  gesamtgewicht_kg: number
  warnungen: string[]
  hinweise: string[]
  stabil: boolean
}
