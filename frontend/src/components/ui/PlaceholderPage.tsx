export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center rounded-xl border border-dashed border-surface-border bg-surface-card/50 p-8 text-center">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 max-w-md text-surface-muted">
        Módulo em desenvolvimento. A navegação e autenticação já estão funcionando.
      </p>
    </div>
  );
}
