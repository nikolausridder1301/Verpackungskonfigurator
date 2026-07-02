import { useRef, useState } from 'react'
import type { UploadFehlerEintrag } from '../types'

interface Props {
  onDatei: (datei: File) => void
  fehler: UploadFehlerEintrag[]
  laeuft: boolean
}

/** Datei-Upload mit zeilenbezogener Fehleranzeige (Issue #19). */
export function UploadBereich({ onDatei, fehler, laeuft }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragAktiv, setDragAktiv] = useState(false)

  const waehleDatei = (dateien: FileList | null) => {
    if (dateien && dateien.length > 0) onDatei(dateien[0])
  }

  return (
    <section className="upload-bereich">
      <div
        className={`upload-zone${dragAktiv ? ' aktiv' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragAktiv(true)
        }}
        onDragLeave={() => setDragAktiv(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragAktiv(false)
          waehleDatei(e.dataTransfer.files)
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          hidden
          onChange={(e) => {
            waehleDatei(e.target.files)
            e.target.value = ''
          }}
        />
        <p className="upload-titel">
          {laeuft ? 'Datei wird geprüft…' : 'Sendungsdatei hierher ziehen oder klicken'}
        </p>
        <p className="upload-hinweis">CSV- oder Excel-Datei (.csv, .xlsx) mit den Artikeln der Sendung</p>
      </div>

      {fehler.length > 0 && (
        <div className="fehler-box" role="alert">
          <strong>Die Datei konnte nicht übernommen werden:</strong>
          <ul>
            {fehler.map((f, i) => (
              <li key={i}>{f.meldung}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
