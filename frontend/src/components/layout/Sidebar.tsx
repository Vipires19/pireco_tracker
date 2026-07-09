"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Car,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LayoutDashboard,
  Monitor,
  RadioTower,
  Settings,
  Truck,
  Users,
  Wallet,
  Wrench,
  X,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/veiculos", label: "Veículos", icon: Car },
  { href: "/rastreadores", label: "Rastreadores", icon: RadioTower },
  { href: "/instalacoes", label: "Instalações", icon: ClipboardList },
  { href: "/operacoes", label: "Operações", icon: Wrench },
  { href: "/monitoramento", label: "Monitoramento", icon: Monitor },
  { href: "/financeiro", label: "Financeiro", icon: Wallet },
  { href: "/configuracoes", label: "Configurações", icon: Settings },
];

type SidebarProps = {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapse: () => void;
  onCloseMobile: () => void;
};

export function Sidebar({
  collapsed,
  mobileOpen,
  onToggleCollapse,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Fechar menu"
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex h-full flex-col border-r border-surface-border bg-surface-card transition-all duration-300",
          collapsed ? "w-20" : "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-surface-border px-4">
          <div className={clsx("flex items-center gap-2", collapsed && "justify-center w-full")}>
            <Truck className="h-6 w-6 text-brand" />
            {!collapsed && <span className="font-semibold">Vehicle Tracker</span>}
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-surface-muted hover:bg-slate-700/50 lg:hidden"
            onClick={onCloseMobile}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={onCloseMobile}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "bg-brand/20 text-brand"
                    : "text-slate-300 hover:bg-slate-700/40 hover:text-white",
                  collapsed && "justify-center px-2",
                )}
                title={collapsed ? label : undefined}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden lg:flex items-center justify-center border-t border-surface-border p-3 text-surface-muted hover:text-white"
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </aside>
    </>
  );
}
