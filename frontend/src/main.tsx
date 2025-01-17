import React from 'react'
import ReactDOM from 'react-dom/client'
import { ContentGeneratorApp } from './components/ContentGeneratorApp'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ContentGeneratorApp />
  </React.StrictMode>,
)
