import React from 'react';
import { Outlet, NavLink } from 'react-router-dom'; // Import NavLink

// Define props to explicitly include children
interface DashboardLayoutProps {
}

const DashboardLayout: React.FC<DashboardLayoutProps> = () => { // Destructure children if needed, though Outlet handles rendering
  // Placeholder layout structure
  return (
    <div className="flex h-screen bg-gray-200">
      {/* Sidebar Placeholder */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-4">SpreadPilot</h2>
        <nav>
          <ul>
            <li>
              <NavLink
                to="/followers"
                className={({ isActive }) =>
                  `block py-2 px-4 rounded hover:bg-gray-700 ${isActive ? 'bg-gray-900' : ''}`
                }
              >
                Followers
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/logs"
                className={({ isActive }) =>
                  `block py-2 px-4 rounded hover:bg-gray-700 ${isActive ? 'bg-gray-900' : ''}`
                }
              >
                Logs
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/commands"
                className={({ isActive }) =>
                  `block py-2 px-4 rounded hover:bg-gray-700 ${isActive ? 'bg-gray-900' : ''}`
                }
              >
                Commands
              </NavLink>
            </li>
            {/* Add more links as needed */}
          </ul>
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header Placeholder */}
        <header className="bg-white shadow p-4">
          <p>Header</p>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
          {/* Nested routes will render via Outlet */}
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;