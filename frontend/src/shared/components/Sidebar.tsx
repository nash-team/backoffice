import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📚' },
]

function handleLogout() {
  // POST to /logout then redirect to login page
  fetch('/logout', { method: 'POST', credentials: 'include' }).finally(() => {
    window.location.href = '/login'
  })
}

export function Sidebar() {
  return (
    <aside className="flex w-64 flex-col bg-sidebar-bg text-sidebar-text">
      <div className="border-b border-primary-700 p-6">
        <h1 className="text-xl font-bold">Ebook Generator</h1>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sidebar-active text-white'
                  : 'hover:bg-sidebar-hover'
              }`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-primary-700 p-4">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded px-4 py-2 text-sm font-medium text-sidebar-text transition-colors hover:bg-sidebar-hover"
        >
          Logout
        </button>
      </div>
    </aside>
  )
}
