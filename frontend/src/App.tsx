import { useEffect, useState } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ok' | 'error'>('checking')

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => (res.ok ? setBackendStatus('ok') : setBackendStatus('error')))
      .catch(() => setBackendStatus('error'))
  }, [])

  return (
    <section id="center">
      <h1>Verpackungskonfigurator</h1>
      <p>
        Backend-Status:{' '}
        {backendStatus === 'checking' && 'wird geprüft…'}
        {backendStatus === 'ok' && '✅ verbunden'}
        {backendStatus === 'error' && '❌ nicht erreichbar (läuft das Backend auf Port 8000?)'}
      </p>
    </section>
  )
}

export default App
