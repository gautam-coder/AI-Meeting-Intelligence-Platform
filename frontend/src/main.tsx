import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './styles.css'
import App from './pages/App'
import UploadPage from './pages/UploadPage'
import Dashboard from './pages/Dashboard'
import MeetingDetail from './pages/MeetingDetail'

const router = createBrowserRouter([
  { path: '/', element: <App />, children: [
    { index: true, element: <Dashboard /> },
    { path: 'upload', element: <UploadPage /> },
    { path: 'meetings/:id', element: <MeetingDetail /> },
  ]},
])

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)

