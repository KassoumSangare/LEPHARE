import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

export const AppLayout = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(() => {
    try { return localStorage.getItem('sidebarCollapsed') === '1'; } catch { return false; }
  });

  const handleToggleSidebar = () => {
    if (window.innerWidth <= 1024) {
      setMobileSidebarOpen((prev) => !prev);
      return;
    }
    setDesktopCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('sidebarCollapsed', next ? '1' : '0'); } catch { /* ignore */ }
      return next;
    });
  };

  return (
    <div className={`app-container ${desktopCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
        <Navbar onToggleMobileSidebar={handleToggleSidebar} />
        <div style={{ display: 'flex', flex: 1, position: 'relative' }}>
          {mobileSidebarOpen && (
            <div
              className="sidebar-backdrop"
              onClick={() => setMobileSidebarOpen(false)}
            />
          )}
          <Sidebar
            isOpen={mobileSidebarOpen}
            onClose={() => setMobileSidebarOpen(false)}
          />
          <main className="main-content">
            <div className="content-body">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default AppLayout;
