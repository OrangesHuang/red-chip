import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

const NAV = [
  { to: '/pool', label: '股票池' },
  { to: '/board', label: '区间看板' },
  { to: '/data', label: '数据管理' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `block px-3 py-2 rounded text-sm transition-colors ${
    isActive
      ? 'bg-gray-800 text-white font-medium'
      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
  }`

function SidebarBrand() {
  return (
    <div className="px-4 py-5 border-b border-gray-800">
      <h1 className="text-lg font-bold text-white leading-tight">红筹高股息</h1>
      <p className="mt-1 text-xs text-gray-500">个股因子分析系统</p>
    </div>
  )
}

function SidebarNav() {
  return (
    <nav className="flex-1 px-3 py-4 space-y-1">
      {NAV.map(item => (
        <NavLink key={item.to} to={item.to} className={linkClass}>
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

function useIsMobile() {
  const [mobile, setMobile] = useState(() => window.innerWidth < 768)
  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return mobile
}

export default function Layout() {
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()

  useEffect(() => { setDrawerOpen(false) }, [location.pathname])

  if (!isMobile) {
    return (
      <div className="flex min-h-screen w-full">
        <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
          <SidebarBrand />
          <SidebarNav />
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
            红筹股 · 高股息因子 · 价格区间与赔率
          </div>
        </aside>
        <main className="flex-1 min-w-0 px-4 py-6">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-dvh w-full">
      <header className="sticky top-0 z-30 flex items-center gap-3 bg-gray-900 border-b border-gray-800 px-4 h-12 shrink-0">
        <button
          onClick={() => setDrawerOpen(true)}
          className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          aria-label="打开导航"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="5" x2="17" y2="5" />
            <line x1="3" y1="10" x2="17" y2="10" />
            <line x1="3" y1="15" x2="17" y2="15" />
          </svg>
        </button>
        <h1 className="text-sm font-bold text-white truncate">红筹高股息</h1>
      </header>

      {drawerOpen && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-gray-900 border-r border-gray-800 flex flex-col animate-slide-in">
            <SidebarBrand />
            <SidebarNav />
            <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
              红筹股 · 高股息因子 · 价格区间与赔率
            </div>
          </aside>
        </div>
      )}

      <main className="flex-1 min-w-0 px-3 py-4">
        <Outlet />
      </main>
    </div>
  )
}
