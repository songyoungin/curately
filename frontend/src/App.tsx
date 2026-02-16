import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import Today from './pages/Today'
import Archive from './pages/Archive'
import Bookmarks from './pages/Bookmarks'
import Rewind from './pages/Rewind'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<Today />} />
            <Route path="/archive" element={<Archive />} />
            <Route path="/bookmarks" element={<Bookmarks />} />
            <Route path="/rewind" element={<Rewind />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
