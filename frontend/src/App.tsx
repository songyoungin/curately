import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import NavBar from './components/NavBar'
import Login from './pages/Login'
import Today from './pages/Today'
import Archive from './pages/Archive'
import Bookmarks from './pages/Bookmarks'
import Digest from './pages/Digest'
import Rewind from './pages/Rewind'
import Settings from './pages/Settings'

function AppLayout() {
  const location = useLocation()

  return (
    <Routes location={location}>
      <Route path="/login" element={<Login />} />
      <Route
        path="*"
        element={
          <ProtectedRoute>
            <div className="min-h-screen bg-gray-50">
              <NavBar />
              <main
                key={location.pathname}
                className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 page-enter"
              >
                <Routes location={location}>
                  <Route path="/" element={<Today />} />
                  <Route path="/digest" element={<Digest />} />
                  <Route path="/archive" element={<Archive />} />
                  <Route path="/bookmarks" element={<Bookmarks />} />
                  <Route path="/rewind" element={<Rewind />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </main>
            </div>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </BrowserRouter>
  )
}
