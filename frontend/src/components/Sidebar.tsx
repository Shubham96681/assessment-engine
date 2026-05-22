"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileUp, Sparkles, FolderOpen, Settings, LogOut } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Upload Content", href: "/upload", icon: FileUp },
    { name: "Generate Assessment", href: "/generate", icon: Sparkles },
    { name: "My Assessments", href: "/assessments", icon: FolderOpen },
  ];

  return (
    <div className="w-64 bg-[#1e293b]/80 backdrop-blur-xl border-r border-[#334155] flex flex-col justify-between p-4 h-full shrink-0 shadow-2xl relative z-10">
      <div>
        <div className="flex items-center gap-3 mb-10 px-2 mt-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-200 to-white">
            Assessment AI
          </h1>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
                  ${isActive 
                    ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner" 
                    : "text-slate-400 hover:bg-[#334155]/50 hover:text-slate-200"
                  }`}
              >
                <item.icon className={`w-5 h-5 transition-transform duration-300 ${isActive ? "scale-110" : "group-hover:scale-110"}`} />
                <span className="font-medium text-sm">{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="space-y-2">
        <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left text-slate-400 hover:bg-[#334155]/50 hover:text-slate-200 transition-all duration-300 group">
          <Settings className="w-5 h-5 group-hover:rotate-45 transition-transform duration-300" />
          <span className="font-medium text-sm">Settings</span>
        </button>
        <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-all duration-300 group">
          <LogOut className="w-5 h-5 group-hover:-translate-x-1 transition-transform duration-300" />
          <span className="font-medium text-sm">Sign Out</span>
        </button>
      </div>
    </div>
  );
}
