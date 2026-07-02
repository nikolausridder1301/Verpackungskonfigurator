import type { Artikel } from './types'

/** Kontraststarke, gut unterscheidbare Farben je Artikeltyp (Issue #24). */
const PALETTE = [
  '#2563eb', // Blau
  '#f59e0b', // Orange
  '#059669', // Grün
  '#dc2626', // Rot
  '#7c3aed', // Violett
  '#0891b2', // Türkis
  '#db2777', // Pink
  '#65a30d', // Oliv
]

export function farbZuordnung(artikel: Artikel[]): Map<string, string> {
  const zuordnung = new Map<string, string>()
  artikel.forEach((a, i) => {
    zuordnung.set(a.artikel_id, PALETTE[i % PALETTE.length])
  })
  return zuordnung
}
