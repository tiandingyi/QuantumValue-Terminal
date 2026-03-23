type ServiceStatus = {
  name: string;
  url: string;
  reachable: boolean;
};

type HandshakeResponse = {
  status: string;
  timestamp: string;
  services: ServiceStatus[];
};

async function getStackStatus(): Promise<HandshakeResponse | null> {
  const apiBaseURL = process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8080";

  try {
    const response = await fetch(`${apiBaseURL}/api/v1/handshake`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as HandshakeResponse;
  } catch {
    return null;
  }
}

export async function StackStatus() {
  const status = await getStackStatus();

  return (
    <section className="animate-rise px-4 md:px-8" style={{ animationDelay: "280ms" }}>
      <div className="mx-auto max-w-6xl border-y border-white/10 py-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Stack health</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Local handshake status</h2>
          </div>
          <p className="max-w-xl text-sm text-slate-400">
            This panel checks the Go gateway from the web app and reports whether the Python engine is reachable behind it.
          </p>
        </div>

        {status ? (
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            {status.services.map((service) => (
              <div key={service.name} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur-xl">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.24em] text-cyan-glow/80">{service.name}</p>
                    <p className="mt-2 break-all font-mono text-xs text-slate-500">{service.url}</p>
                  </div>
                  <span
                    className={`inline-flex rounded-full px-3 py-1 text-xs uppercase tracking-[0.2em] ${
                      service.reachable
                        ? "bg-emerald-500/15 text-emerald-300"
                        : "bg-amber-500/15 text-amber-300"
                    }`}
                  >
                    {service.reachable ? "reachable" : "waiting"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-6 rounded-3xl border border-dashed border-white/10 bg-black/10 p-5 text-sm text-slate-400">
            Stack handshake is unavailable. Start the Docker stack or run the Go gateway locally on `localhost:8080`.
          </div>
        )}
      </div>
    </section>
  );
}
