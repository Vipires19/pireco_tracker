"use client";

import { LogOut, Menu, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

type HeaderProps = {
  onOpenMobileMenu: () => void;
};

export function Header({ onOpenMobileMenu }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-surface-border bg-surface/80 px-4 backdrop-blur md:px-6">
      <button
        type="button"
        className="rounded-lg p-2 text-surface-muted hover:bg-slate-700/40 lg:hidden"
        onClick={onOpenMobileMenu}
        aria-label="Abrir menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="hidden lg:block">
        <p className="text-sm text-surface-muted">ERP White Label</p>
        <p className="text-xs text-slate-500">Sprint 2 — CRM Clientes</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 rounded-lg bg-surface-card px-3 py-2 text-sm">
          <User className="h-4 w-4 text-brand" />
          <span>{user?.full_name}</span>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/40"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Sair</span>
        </button>
      </div>
    </header>
  );
}
