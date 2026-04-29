"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { ContractCandidate, GovernedFinding } from "@/types/governance";

type HealthPayload = {
  ok: boolean;
  db: string;
  dataset: string;
};

type CasesPayload = {
  ok: boolean;
  cases: ContractCandidate[];
  dataset: string;
  source: string;
  error?: string;
};

type GovernPayload = {
  ok: boolean;
  finding?: GovernedFinding;
  error?: string;
};

type ExportPayload = {
  ok: boolean;
  destination?: {
    bucket: string;
    key: string;
    region: string;
  };
  error?: string;
};

const currency = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 0,
});

function money(value: number) {
  return currency.format(value);
}

function percent(value: number) {
  return `${(value * 100).toLocaleString("en-CA", { maximumFractionDigits: 0 })}%`;
}

function displaySummary(value: string) {
  return value.replace(/\*\*/g, "");
}

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export default function Home() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [cases, setCases] = useState<ContractCandidate[]>([]);
  const [selectedReference, setSelectedReference] = useState<string>("");
  const [finding, setFinding] = useState<GovernedFinding | null>(null);
  const [summary, setSummary] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingFinding, setLoadingFinding] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const selectedCase = useMemo(
    () => cases.find((candidate) => candidate.reference_number === selectedReference) ?? cases[0],
    [cases, selectedReference],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setError("");
      setLoadingCases(true);

      try {
        const [healthResponse, casesResponse] = await Promise.all([
          fetch("/api/health", { cache: "no-store" }),
          fetch("/api/cases?limit=12", { cache: "no-store" }),
        ]);
        const healthPayload = (await healthResponse.json()) as HealthPayload;
        const casesPayload = (await casesResponse.json()) as CasesPayload;

        if (!casesPayload.ok) {
          throw new Error(casesPayload.error ?? "Unable to load cases");
        }

        if (!cancelled) {
          setHealth(healthPayload);
          setCases(casesPayload.cases);
          setSelectedReference(casesPayload.cases[0]?.reference_number ?? "");
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setLoadingCases(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function governSelectedCase() {
      if (!selectedCase) return;

      setLoadingFinding(true);
      setFinding(null);
      setSummary("");
      setExportPath("");
      setError("");

      try {
        const response = await fetch("/api/govern", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contract: selectedCase }),
        });
        const payload = (await response.json()) as GovernPayload;

        if (!payload.ok || !payload.finding) {
          throw new Error(payload.error ?? "Unable to run governance");
        }

        if (!cancelled) {
          setFinding(payload.finding);
        }
      } catch (governError) {
        if (!cancelled) {
          setError(governError instanceof Error ? governError.message : "Unable to run governance");
        }
      } finally {
        if (!cancelled) {
          setLoadingFinding(false);
        }
      }
    }

    governSelectedCase();

    return () => {
      cancelled = true;
    };
  }, [selectedCase]);

  async function explainFinding() {
    if (!finding) return;

    setLoadingSummary(true);
    setError("");

    try {
      const response = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding }),
      });
      const payload = (await response.json()) as { ok: boolean; summary?: string; error?: string };

      if (!payload.ok) {
        throw new Error(payload.error ?? "Unable to generate summary");
      }

      setSummary(payload.summary ?? "");
    } catch (summaryError) {
      setError(summaryError instanceof Error ? summaryError.message : "Unable to generate summary");
    } finally {
      setLoadingSummary(false);
    }
  }

  async function exportCases() {
    setExporting(true);
    setError("");

    try {
      const response = await fetch("/api/exports/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 12 }),
      });
      const payload = (await response.json()) as ExportPayload;

      if (!payload.ok || !payload.destination) {
        throw new Error(payload.error ?? "Unable to export cases");
      }

      setExportPath(`${payload.destination.bucket}/${payload.destination.key}`);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Unable to export cases");
    } finally {
      setExporting(false);
    }
  }

  const investigatedCount = cases.filter((candidate) => candidate.amendment_ratio >= 1).length;

  return (
    <main className="min-h-screen bg-[#f5f7f4] text-[#15201c]">
      <section className="border-b border-[#d9dfd7] bg-[#fbfcfa]">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 md:px-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#3f6f65]">
                Oil City Hackers
              </p>
              <h1 className="text-3xl font-semibold tracking-normal md:text-4xl">
                Amendment Creep Review Console
              </h1>
            </div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <StatusTile label="Database" value={health?.db ?? "checking"} good={health?.db === "connected"} />
              <StatusTile label="Dataset" value={health?.dataset ?? "loading"} good={health?.dataset === "alberta"} />
              <StatusTile label="Cases" value={loadingCases ? "..." : String(cases.length)} good={cases.length > 0} />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="Reviewed candidates" value={loadingCases ? "Loading" : cases.length.toLocaleString("en-CA")} />
            <Metric label="High-growth set" value={loadingCases ? "Loading" : investigatedCount.toLocaleString("en-CA")} />
            <Metric
              label="Top amendment ratio"
              value={cases[0] ? percent(cases[0].amendment_ratio) : "No data"}
            />
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 py-5 md:grid-cols-[minmax(340px,0.9fr)_minmax(0,1.4fr)] md:px-8">
        <aside className="min-h-[640px] border border-[#d9dfd7] bg-white">
          <div className="flex items-center justify-between border-b border-[#d9dfd7] px-4 py-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#4b5f59]">
              Ranked Cases
            </h2>
            <button
              className="h-9 border border-[#b8c4bd] px-3 text-sm font-medium text-[#1f3f38] transition hover:bg-[#eef4f1] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={exporting || cases.length === 0}
              onClick={exportCases}
              type="button"
            >
              {exporting ? "Exporting" : "Export"}
            </button>
          </div>

          <div className="max-h-[590px] overflow-y-auto">
            {loadingCases ? (
              <div className="px-4 py-6 text-sm text-[#66736d]">Loading cases...</div>
            ) : (
              cases.map((candidate) => (
                <button
                  className={classNames(
                    "grid w-full gap-2 border-b border-[#edf0ec] px-4 py-4 text-left transition hover:bg-[#f6faf8]",
                    selectedCase?.reference_number === candidate.reference_number && "bg-[#edf6f2]",
                  )}
                  key={candidate.reference_number}
                  onClick={() => setSelectedReference(candidate.reference_number)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-sm font-semibold text-[#17231f]">{candidate.vendor_name}</span>
                    <span className="whitespace-nowrap bg-[#f3efe6] px-2 py-1 text-xs font-semibold text-[#725f24]">
                      {percent(candidate.amendment_ratio)}
                    </span>
                  </div>
                  <span className="text-xs text-[#66736d]">{candidate.department}</span>
                  <div className="flex items-center justify-between text-xs text-[#4f5f59]">
                    <span>{candidate.reference_number}</span>
                    <span>{money(candidate.current_value)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="flex min-h-[640px] flex-col border border-[#d9dfd7] bg-white">
          {selectedCase ? (
            <>
              <div className="border-b border-[#d9dfd7] px-5 py-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-[#3f6f65]">{selectedCase.reference_number}</p>
                    <h2 className="text-2xl font-semibold tracking-normal">{selectedCase.vendor_name}</h2>
                    <p className="max-w-3xl text-sm leading-6 text-[#5d6a65]">{selectedCase.description}</p>
                  </div>
                  <ClassificationBadge value={finding?.claim_state ?? (loadingFinding ? "RUNNING" : "PENDING")} />
                </div>
              </div>

              <div className="grid gap-4 border-b border-[#d9dfd7] px-5 py-4 md:grid-cols-4">
                <Metric label="Original value" value={money(selectedCase.original_value)} compact />
                <Metric label="Amendment value" value={money(selectedCase.amendment_value)} compact />
                <Metric label="Current value" value={money(selectedCase.current_value)} compact />
                <Metric label="Growth ratio" value={percent(selectedCase.amendment_ratio)} compact />
              </div>

              <div className="grid flex-1 gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-5">
                  <Panel title="Governed Finding">
                    {loadingFinding || !finding ? (
                      <p className="text-sm text-[#66736d]">Running deterministic governance...</p>
                    ) : (
                      <div className="space-y-4">
                        <h3 className="text-xl font-semibold tracking-normal">{finding.headline}</h3>
                        <FindingRow label="What we found" value={finding.what_we_found} />
                        <FindingRow label="What we did not find" value={finding.what_we_did_not_find} />
                        <FindingRow label="Next step" value={finding.next_step} />
                      </div>
                    )}
                  </Panel>

                  <Panel
                    action={
                      <button
                        className="h-9 border border-[#b8c4bd] px-3 text-sm font-medium text-[#1f3f38] transition hover:bg-[#eef4f1] disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={!finding || loadingSummary}
                        onClick={explainFinding}
                        type="button"
                      >
                        {loadingSummary ? "Summarizing" : "Bedrock Summary"}
                      </button>
                    }
                    title="Explanation"
                  >
                    <p className="text-sm leading-6 text-[#4d5d57]">
                      {summary ? displaySummary(summary) : "No generated summary yet."}
                    </p>
                  </Panel>
                </div>

                <div className="space-y-5">
                  <Panel title="Gate Results">
                    <div className="space-y-2">
                      {(finding?.gates ?? []).map((gate) => (
                        <div className="border border-[#e2e7e0] px-3 py-3" key={gate.gate_id}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-semibold">{gate.gate_id}</span>
                            <span className="text-xs font-semibold uppercase text-[#3f6f65]">
                              {gate.verdict}
                            </span>
                          </div>
                          <p className="mt-1 text-xs leading-5 text-[#68756f]">{gate.gate_name}</p>
                        </div>
                      ))}
                      {!finding && <p className="text-sm text-[#66736d]">Awaiting governance run...</p>}
                    </div>
                  </Panel>

                  <Panel title="Flight Recorder">
                    <div className="space-y-3">
                      {(finding?.flight_recorder.slice(-4) ?? []).map((entry) => (
                        <div key={entry.id} className="border-l-2 border-[#9eb8ad] pl-3">
                          <p className="text-xs font-semibold text-[#1f3f38]">{entry.action}</p>
                          <p className="mt-1 text-xs leading-5 text-[#68756f]">{entry.stage}</p>
                        </div>
                      ))}
                      {!finding && <p className="text-sm text-[#66736d]">No entries yet.</p>}
                    </div>
                  </Panel>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-[#66736d]">
              No cases available.
            </div>
          )}
        </section>
      </section>

      {(error || exportPath) && (
        <section className="mx-auto max-w-7xl px-5 pb-6 md:px-8">
          <div
            className={classNames(
              "border px-4 py-3 text-sm",
              error ? "border-[#d7a2a2] bg-[#fff7f7] text-[#7b2b2b]" : "border-[#cddbbf] bg-[#f5fbef] text-[#2f5a32]",
            )}
          >
            {error || `Exported snapshot to ${exportPath}`}
          </div>
        </section>
      )}
    </main>
  );
}

function StatusTile({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="border border-[#d9dfd7] bg-white px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[#69766f]">{label}</p>
      <p className={classNames("mt-1 text-sm font-semibold", good ? "text-[#287260]" : "text-[#8a5b1f]")}>
        {value}
      </p>
    </div>
  );
}

function Metric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={classNames("border border-[#d9dfd7] bg-white", compact ? "px-3 py-3" : "px-4 py-4")}>
      <p className="text-xs font-semibold uppercase tracking-wide text-[#69766f]">{label}</p>
      <p className={classNames("mt-2 font-semibold tracking-normal", compact ? "text-lg" : "text-2xl")}>
        {value}
      </p>
    </div>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border border-[#d9dfd7]">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-[#d9dfd7] px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#4b5f59]">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function FindingRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-[#69766f]">{label}</p>
      <p className="mt-1 text-sm leading-6 text-[#4d5d57]">{value}</p>
    </div>
  );
}

function ClassificationBadge({ value }: { value: string }) {
  const tone =
    value === "INVESTIGATED"
      ? "border-[#c6973d] bg-[#fff8e8] text-[#7b5818]"
      : value === "FLAGGED"
        ? "border-[#d7b46c] bg-[#fffaf0] text-[#755b1b]"
        : value === "CLEARED"
          ? "border-[#a8cfb5] bg-[#f1fbf4] text-[#25633d]"
          : "border-[#c7d0ca] bg-[#f7f9f7] text-[#53605a]";

  return (
    <div className={classNames("w-fit border px-4 py-3 text-center", tone)}>
      <p className="text-[11px] font-semibold uppercase tracking-wide">Classification</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  );
}
