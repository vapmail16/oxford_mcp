import { useState } from 'react'
import LandingPage from './pages/LandingPage'
import TeachingPipelinePage from './pages/TeachingPipelinePage'
import Chatbot from './components/Chatbot'

function App() {
  const [page, setPage] = useState<'home' | 'teaching'>('home')

  return (
    <>
      {page === 'home' ? (
        <LandingPage onOpenTeaching={() => setPage('teaching')} />
      ) : (
        <TeachingPipelinePage onBackHome={() => setPage('home')} />
      )}
      <Chatbot />
    </>
  )
}

export default App
