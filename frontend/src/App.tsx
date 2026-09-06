import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/common/Layout'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import DataManage from './pages/DataManage'

export default function App() {
  return (
    <BrowserRouter basename={__APP_BASE__ || undefined}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/pool" replace />} />
          <Route path="/pool" element={<Dashboard />} />
          <Route path="/stock/:code" element={<StockDetail />} />
          <Route path="/data" element={<DataManage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
