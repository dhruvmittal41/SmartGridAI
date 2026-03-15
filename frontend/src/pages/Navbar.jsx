import { Link } from "react-router-dom";

export default function Navbar(){

  return (

    <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur border-b border-slate-800">

      <div className="max-w-7xl mx-auto flex justify-between items-center px-8 py-5">

        {/* Logo */}

        <Link to="/" className="text-2xl font-bold text-sky-400 hover:scale-105 transition">
          ⚡ SmartGrid AI
        </Link>


        {/* Nav Links */}

        <div className="space-x-8 text-lg hidden md:flex">

          <a
            href="#features"
            className="text-slate-300 hover:text-sky-400 transition"
          >
            Features
          </a>

          <a
            href="#about"
            className="text-slate-300 hover:text-sky-400 transition"
          >
            About
          </a>

          <a
            href="#stats"
            className="text-slate-300 hover:text-sky-400 transition"
          >
            Stats
          </a>

        </div>


        {/* Button */}

        <Link to="/National">

          <button className="px-5 py-2 bg-green-500 rounded-lg hover:scale-105 transition text-sm font-medium">
            Grid Dashboard
          </button>

        </Link>

      </div>

    </nav>

  );
}