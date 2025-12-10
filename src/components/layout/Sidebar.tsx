"use client";
import React from "react";
import { motion } from "framer-motion";
import {
  Upload,
  Database,
  BarChart3,
  Cpu,
  Activity,
  Dna,
  Settings,
  HelpCircle,
} from "lucide-react";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  gradient: string;
}

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const navItems: NavItem[] = [
  {
    id: "upload",
    label: "Genome Upload",
    icon: <Upload className="w-5 h-5" />,
    gradient: "revolut-gradient-blue",
  },
  {
    id: "database",
    label: "Genome Database",
    icon: <Database className="w-5 h-5" />,
    gradient: "revolut-gradient-purple",
  },
  {
    id: "results",
    label: "Results Dashboard",
    icon: <BarChart3 className="w-5 h-5" />,
    gradient: "revolut-gradient-green",
  },
  {
    id: "training",
    label: "Model Training",
    icon: <Cpu className="w-5 h-5" />,
    gradient: "revolut-gradient-orange",
  },
  {
    id: "training-status",
    label: "Training Status",
    icon: <Activity className="w-5 h-5" />,
    gradient: "revolut-gradient-pink",
  },
];

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-card border-r border-border flex flex-col z-50">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl revolut-gradient-blue flex items-center justify-center">
            <Dna className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">Antibiogram</h1>
            <p className="text-xs text-muted-foreground">AI Predictor</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-2">
          Analysis
        </p>
        {navItems.map((item) => (
          <motion.button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={`w-full revolut-nav-item ${
              activeTab === item.id ? "active" : ""
            }`}
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.98 }}
          >
            <div
              className={`feature-icon ${item.gradient} ${
                activeTab === item.id ? "opacity-100" : "opacity-60"
              }`}
              style={{ width: "36px", height: "36px" }}
            >
              <span className="text-white">{item.icon}</span>
            </div>
            <span className="font-medium">{item.label}</span>
          </motion.button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-1">
        <button className="w-full revolut-nav-item">
          <Settings className="w-5 h-5" />
          <span>Settings</span>
        </button>
        <button className="w-full revolut-nav-item">
          <HelpCircle className="w-5 h-5" />
          <span>Help & Support</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
