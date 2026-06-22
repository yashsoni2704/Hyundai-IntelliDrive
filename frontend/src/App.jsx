import { AuthProvider } from './contexts/AuthContext'
import { useAuth } from './contexts/AuthContext'
import AdminDashboard from './pages/AdminDashboard'
import ChatPage from './pages/ChatPage'

function AppContent() {
  const { user } = useAuth()
  return user?.is_admin ? <AdminDashboard /> : <ChatPage />
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
