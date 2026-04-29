const endpoints = [
  { method: "GET", path: "/api/health", description: "API and database smoke test" },
  { method: "GET", path: "/api/db/schema", description: "List available GovAlta schemas/tables" },
  { method: "GET", path: "/api/cases", description: "Ranked contract candidates" },
  { method: "GET", path: "/api/cases/DEMO-INV-001", description: "Single candidate detail" },
  { method: "POST", path: "/api/govern", description: "Governance finding for a ContractCandidate" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto flex max-w-5xl flex-col gap-8">
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">
            Oil City Hackers API
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal">
            Governance-ready contract case API
          </h1>
          <p className="max-w-3xl text-base leading-7 text-slate-700">
            Dev 2 scaffold for ranked cases, database schema probing, and the
            governance endpoint Dev 3 will connect to. Mock data is enabled until
            `DATABASE_URL` and `CASE_DATASET` are configured.
          </p>
        </div>

        <div className="overflow-hidden border border-slate-200 bg-white">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-4 py-3 font-semibold">Method</th>
                <th className="px-4 py-3 font-semibold">Path</th>
                <th className="px-4 py-3 font-semibold">Purpose</th>
              </tr>
            </thead>
            <tbody>
              {endpoints.map((endpoint) => (
                <tr key={endpoint.path} className="border-t border-slate-200">
                  <td className="px-4 py-3 font-mono text-xs text-teal-700">
                    {endpoint.method}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{endpoint.path}</td>
                  <td className="px-4 py-3 text-slate-700">{endpoint.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
