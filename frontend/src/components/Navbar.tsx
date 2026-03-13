import { NavLink } from "react-router-dom";

export default function Navbar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg font-medium transition-colors ${
      isActive
        ? "bg-blue-600 text-white"
        : "text-gray-300 hover:text-white hover:bg-gray-800"
    }`;

  return (
    <nav className="bg-gray-900 border-b border-gray-800 shadow-lg">
      <div className="container mx-auto px-4 max-w-7xl flex items-center justify-between h-16">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚙️</span>
          <span className="font-bold text-lg text-white tracking-tight">
            IoT Maintenance Predictor
          </span>
        </div>
        <div className="flex gap-2">
          <NavLink to="/" end className={linkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/trends" className={linkClass}>
            Trends
          </NavLink>
        </div>
      </div>
    </nav>
  );
}
