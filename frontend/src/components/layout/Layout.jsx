import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { FileText, LogOut } from "lucide-react";

export default function Layout() {
  const { logout, user } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-primary-600">DocQA</h1>
          <p className="text-xs text-gray-400 mt-0.5">AI Document Assistant</p>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`
            }
          >
            <FileText size={17} />
            Documents
          </NavLink>
        </nav>

        <div className="p-4 border-t border-gray-200">
          {user?.email && (
            <p className="text-xs text-gray-400 truncate mb-3">{user.email}</p>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-red-600 transition-colors"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
