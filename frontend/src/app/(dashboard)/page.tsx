"use client";

import { useEffect, useState, type ElementType } from "react";
import { Activity, Car, Users, Wifi, WifiOff } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { fetchDashboardOverview, type DashboardOverview } from "@/lib/auth";

function StatCard({
  title,
  value,
  icon: Icon,
  accent,
}: {
  title: string;
  value: number;
  icon: ElementType;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-surface-muted">{title}</p>
          <p className="mt-2 text-3xl font-bold">{value}</p>
        </div>
        <div className={`rounded-lg p-2 ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { accessToken } = useAuth();
  const [stats, setStats] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    const load = () => {
      void fetchDashboardOverview(accessToken).then(setStats).catch(() => setStats(null));
    };
    load();
    const timer = window.setInterval(load, 15_000);
    return () => window.clearInterval(timer);
  }, [accessToken]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-surface-muted">Visão geral da operação</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Clientes" value={stats?.clients ?? 0} icon={Users} accent="bg-blue-500/20 text-blue-400" />
        <StatCard title="Veículos" value={stats?.vehicles ?? 0} icon={Car} accent="bg-emerald-500/20 text-emerald-400" />
        <StatCard title="Online" value={stats?.online ?? 0} icon={Wifi} accent="bg-green-500/20 text-green-400" />
        <StatCard title="Offline" value={stats?.offline ?? 0} icon={WifiOff} accent="bg-orange-500/20 text-orange-400" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-surface-border bg-surface-card p-5 lg:col-span-1">
          <h2 className="font-semibold">Centro de Pendências</h2>
          <p className="mt-2 text-sm text-surface-muted">Placeholder — em breve</p>
          <div className="mt-4 flex h-32 items-center justify-center rounded-lg border border-dashed border-surface-border text-surface-muted">
            <Activity className="h-6 w-6" />
          </div>
        </section>

        <section className="rounded-xl border border-surface-border bg-surface-card p-5 lg:col-span-2">
          <h2 className="font-semibold">Mapa</h2>
          <p className="mt-2 text-sm text-surface-muted">Placeholder — monitoramento na próxima sprint</p>
          <div className="mt-4 flex h-48 items-center justify-center rounded-lg border border-dashed border-surface-border bg-slate-900/50 text-surface-muted">
            Mapa em desenvolvimento
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-surface-border bg-surface-card/60 p-4">
        <p className="text-sm text-surface-muted">
          Assistente IA — placeholder discreto para integração futura.
        </p>
      </section>
    </div>
  );
}
