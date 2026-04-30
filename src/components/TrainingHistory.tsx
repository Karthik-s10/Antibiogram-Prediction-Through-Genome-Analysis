"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { listJobs, pinJob, unpinJob, clearUnpinnedJobs, getJobStatus, getXGBoostExplainability, blastKmers, type JobStatus } from "@/services/apiClient";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Clock, Pin, PinOff, History, Trash2, BarChart3 } from "lucide-react";

interface TrainingHistoryProps {
  onSelectJob?: (jobId: string, jobType: string) => void;
}

const TrainingHistory: React.FC<TrainingHistoryProps> = ({ onSelectJob }) => {
  const [jobs, setJobs] = useState<Array<Partial<JobStatus> & { pinned?: boolean }>>([]);
  const [selectedJob, setSelectedJob] = useState<{ jobId: string; jobType: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [compareJobs, setCompareJobs] = useState<Record<string, JobStatus | null>>({});
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const [explainJob, setExplainJob] = useState<JobStatus | null>(null);
  const [explainData, setExplainData] = useState<any | null>(null);
  const [isLoadingExplain, setIsLoadingExplain] = useState(false);
  const [blastResults, setBlastResults] = useState<Record<string, any[]>>({});
  const [isRunningBlast, setIsRunningBlast] = useState(false);
  const [showPinnedMiniVisuals, setShowPinnedMiniVisuals] = useState(true);

  const loadJobs = async () => {
    try {
      setIsLoading(true);
      const data = await listJobs();
      setJobs(data.jobs || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load training jobs");
    } finally {
      setIsLoading(false);
    }
  };

  const openExplainability = async (jobId: string) => {
    try {
      setIsLoadingExplain(true);
      setExplainData(null);
      setBlastResults({});

      const status = await getJobStatus(jobId);
      setExplainJob(status);

      const metrics: any = status.metrics || {};
      const modelName = metrics.model_name || status.metadata?.model_name || jobId;

      const data = await getXGBoostExplainability(modelName);
      setExplainData(data);
    } catch (err: any) {
      setError(err.message || "Failed to load explainability report");
      setExplainJob(null);
      setExplainData(null);
    } finally {
      setIsLoadingExplain(false);
    }
  };

  const runBlastForTopKmers = async () => {
    if (!explainData || !explainData.antibiotics) return;
    try {
      setIsRunningBlast(true);
      const kmers = new Set<string>();

      Object.values(explainData.antibiotics as any).forEach((ab: any) => {
        const topFeatures: any[] = ab.top_features || [];
        topFeatures.slice(0, 3).forEach((feat) => {
          if (typeof feat.feature === "string") kmers.add(feat.feature);
        });
      });

      if (kmers.size === 0) {
        setIsRunningBlast(false);
        return;
      }

      const resp = await blastKmers(Array.from(kmers), 1);
      setBlastResults(resp.kmers || {});
    } catch (err: any) {
      setError(err.message || "BLAST lookup failed");
    } finally {
      setIsRunningBlast(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  // Load details for comparison when two jobs are selected
  useEffect(() => {
    const loadComparison = async () => {
      if (compareSelection.length !== 2) {
        setCompareJobs({});
        return;
      }
      try {
        setIsLoadingCompare(true);
        const [jobA, jobB] = compareSelection;
        const [statusA, statusB] = await Promise.all([
          getJobStatus(jobA),
          getJobStatus(jobB),
        ]);
        setCompareJobs({
          [jobA]: statusA,
          [jobB]: statusB,
        });
      } catch (err: any) {
        setError(err.message || "Failed to load comparison jobs");
      } finally {
        setIsLoadingCompare(false);
      }
    };

    loadComparison();
  }, [compareSelection]);

  const handlePinToggle = async (jobId: string, pinned?: boolean) => {
    try {
      if (pinned) {
        await unpinJob(jobId);
      } else {
        await pinJob(jobId);
      }
      await loadJobs();
    } catch (err: any) {
      setError(err.message || "Failed to update pin state");
    }
  };

  const handleClearUnpinned = async () => {
    try {
      setIsClearing(true);
      await clearUnpinnedJobs();
      await loadJobs();
    } catch (err: any) {
      setError(err.message || "Failed to clear jobs");
    } finally {
      setIsClearing(false);
    }
  };

  const handleSelectJob = (jobId: string, jobType: string) => {
    setSelectedJob({ jobId, jobType });
    if (onSelectJob) {
      onSelectJob(jobId, jobType);
    }
  };

  const toggleCompareSelection = (jobId: string) => {
    setCompareSelection((prev) => {
      if (prev.includes(jobId)) {
        return prev.filter((id) => id !== jobId);
      }
      if (prev.length >= 2) {
        // Keep the most recent two selections
        return [prev[1], jobId];
      }
      return [...prev, jobId];
    });
  };

  const getStatusBadgeVariant = (status?: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-300";
      case "failed":
        return "bg-red-100 text-red-800 border-red-300";
      case "running":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "pending":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "cancelled":
        return "bg-orange-100 text-orange-800 border-orange-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const sortedJobs = [...jobs].sort((a, b) => {
    const aPinned = a.pinned ?? false;
    const bPinned = b.pinned ?? false;
    if (aPinned !== bPinned) {
      return aPinned ? -1 : 1;
    }
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    return bTime - aTime;
  });

  return (
    <div className="w-full max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-slate-300" />
          <h2 className="text-lg font-semibold text-slate-100">Training History</h2>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showPinnedMiniVisuals ? "default" : "outline"}
            size="sm"
            onClick={() => setShowPinnedMiniVisuals((prev) => !prev)}
            className="flex items-center gap-2"
          >
            <BarChart3 className="h-4 w-4" />
            <span className="text-xs">
              {showPinnedMiniVisuals ? "Hide mini visuals" : "Show mini visuals for pinned runs"}
            </span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearUnpinned}
            disabled={isClearing || isLoading || sortedJobs.length === 0}
            className="flex items-center gap-2"
          >
            <Trash2 className="h-4 w-4" />
            {isClearing ? "Clearing..." : "Clear Unpinned"}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {explainJob && (
        <div className="mt-6 border rounded-lg p-4 bg-white shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-800">XGBoost Explainability</h3>
              <p className="text-xs text-slate-500 mt-1">
                Model: {explainData?.model_name || explainJob.metadata?.model_name || explainJob.job_id}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setExplainJob(null);
                setExplainData(null);
                setBlastResults({});
              }}
            >
              Close
            </Button>
          </div>

          {isLoadingExplain && (
            <p className="text-xs text-slate-500">Loading explainability report...</p>
          )}

          {explainData && explainData.antibiotics && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-600">
                  Top k-mers per antibiotic (from XGBoost feature importances)
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isRunningBlast}
                  onClick={runBlastForTopKmers}
                >
                  {isRunningBlast ? "Running BLAST..." : "Annotate with BLAST"}
                </Button>
              </div>
              <div className="border rounded-md max-h-80 overflow-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-2 py-1 text-left">Antibiotic</th>
                      <th className="px-2 py-1 text-left">k-mer</th>
                      <th className="px-2 py-1 text-right">Importance</th>
                      <th className="px-2 py-1 text-left">BLAST hit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(explainData.antibiotics as any).map(
                      ([antibiotic, abData]: [string, any]) => {
                        const topFeatures: any[] = abData.top_features || [];
                        if (!topFeatures.length) return null;
                        return topFeatures.slice(0, 5).map((feat, idx) => {
                          const hits = blastResults[feat.feature] || [];
                          const hit = hits[0];
                          return (
                            <tr key={`${antibiotic}-${feat.feature}-${idx}`} className="odd:bg-white even:bg-slate-50">
                              <td className="px-2 py-1 align-top capitalize">
                                {idx === 0 ? antibiotic : ""}
                              </td>
                              <td className="px-2 py-1 align-top font-mono text-[11px]">
                                {feat.feature}
                              </td>
                              <td className="px-2 py-1 align-top text-right">
                                {typeof feat.importance === "number"
                                  ? feat.importance.toExponential(2)
                                  : "-"}
                              </td>
                              <td className="px-2 py-1 align-top text-[11px] text-slate-700">
                                {hit ? (
                                  <div className="space-y-0.5">
                                    <div className="font-medium truncate" title={hit.title}>
                                      {hit.title || hit.hit_id || "Unknown"}
                                    </div>
                                    <div className="text-slate-500">
                                      {hit.identity !== null && hit.identity !== undefined && (
                                        <span className="mr-2">
                                          Identity {(hit.identity * 100).toFixed(1)}%
                                        </span>
                                      )}
                                      {hit.evalue !== null && hit.evalue !== undefined && (
                                        <span>E={hit.evalue}</span>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-slate-400">No BLAST hit</span>
                                )}
                              </td>
                            </tr>
                          );
                        });
                      },
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {sortedJobs.length === 0 && !isLoading && (
        <Card>
          <CardContent className="py-6 flex items-center gap-3 text-sm text-slate-600">
            <Clock className="h-4 w-4" />
            No training jobs yet. Start a training run to see it appear here.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <Card>
          <CardContent className="py-6 text-sm text-slate-600">
            Loading training jobs...
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-3">
        {sortedJobs.map((job) => {
          const jobId = job.job_id as string;
          const jobType = job.job_type as string;
          const status = job.status as string | undefined;
          const pinned = job.pinned ?? false;
          const modelName = (job as any).metadata?.model_name || jobId;
          const isCompared = compareSelection.includes(jobId);

          const metrics: any = (job as any).metrics || {};
          const perMetrics: any = metrics.per_antibiotic_metrics || {};
          const hasPerMetrics =
            pinned &&
            status === "completed" &&
            perMetrics &&
            Object.keys(perMetrics).length > 0;

          let miniHeatmap: React.ReactNode = null;

          if (showPinnedMiniVisuals && hasPerMetrics) {
            const antibiotics = Object.keys(perMetrics).sort();
            if (antibiotics.length > 0) {
              const classDefs = [
                { key: "0", label: "S", name: "Susceptible", rgb: "34,197,94" },
                { key: "1", label: "I", name: "Intermediate", rgb: "245,158,11" },
                { key: "2", label: "R", name: "Resistant", rgb: "239,68,68" },
              ];

              let maxSupport = 0;
              antibiotics.forEach((ab) => {
                const m = perMetrics[ab] || {};
                const perClass = m.per_class || {};
                classDefs.forEach(({ key }) => {
                  const cls = perClass[key] || {};
                  const support = typeof cls["support"] === "number" ? (cls["support"] as number) : 0;
                  if (support > maxSupport) maxSupport = support;
                });
              });
              if (maxSupport <= 0) maxSupport = 1;

              // Prepare tiny F1 (macro) sparkline data per antibiotic
              const f1Values: number[] = [];
              let maxF1 = 0;
              antibiotics.forEach((ab) => {
                const m = perMetrics[ab] || {};
                const f1 = typeof m.f1_macro === "number" ? (m.f1_macro as number) : 0;
                f1Values.push(f1);
                if (f1 > maxF1) maxF1 = f1;
              });
              if (maxF1 <= 0) maxF1 = 1;

              const sparkWidth = 120;
              const sparkHeight = 24;
              const sparkPadding = 3;
              const denom = Math.max(antibiotics.length - 1, 1);
              const sparkPoints = antibiotics
                .map((ab, idx) => {
                  const vRaw = f1Values[idx] ?? 0;
                  const v = Math.max(0, vRaw);
                  const x = (idx / denom) * (sparkWidth - sparkPadding * 2) + sparkPadding;
                  const y =
                    (sparkHeight - sparkPadding) - (v / maxF1) * (sparkHeight - sparkPadding * 2);
                  return `${x},${y}`;
                })
                .join(" ");

              miniHeatmap = (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span className="truncate">Class distribution (S/I/R)</span>
                    <div className="flex gap-2">
                      <span className="flex items-center gap-1">
                        <span className="inline-block w-3 h-3 rounded-[2px] bg-emerald-400" /> S
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="inline-block w-3 h-3 rounded-[2px] bg-amber-400" /> I
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="inline-block w-3 h-3 rounded-[2px] bg-rose-400" /> R
                      </span>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <div className="flex gap-[3px] py-1">
                      {antibiotics.map((ab) => {
                        const m = perMetrics[ab] || {};
                        const perClass = m.per_class || {};
                        return (
                          <div key={ab} className="flex flex-col gap-[2px] items-stretch">
                            {classDefs.map((cls) => {
                              const cData = (perClass && perClass[cls.key]) || {};
                              const support =
                                typeof cData["support"] === "number" ? (cData["support"] as number) : 0;
                              const intensity = maxSupport > 0 ? support / maxSupport : 0;
                              const alpha = 0.15 + 0.8 * intensity;
                              const bgColor = `rgba(${cls.rgb}, ${alpha.toFixed(3)})`;
                              return (
                                <div
                                  key={`${ab}-${cls.key}`}
                                  className="w-3 h-2.5 rounded-[2px]"
                                  style={{ backgroundColor: bgColor }}
                                  title={`${ab} · ${cls.name} · samples=${support}`}
                                />
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  {/* Tiny F1 macro sparkline */}
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-500">
                    <span className="whitespace-nowrap">F1 (macro)</span>
                    <svg
                      viewBox={`0 0 ${sparkWidth} ${sparkHeight}`}
                      className="h-4 flex-1 text-slate-400"
                    >
                      <polyline
                        points={sparkPoints}
                        fill="none"
                        stroke="#3b82f6"
                        strokeWidth={1.5}
                      />
                    </svg>
                  </div>
                </div>
              );
            }
          }

          return (
            <Card
              key={jobId}
              className={`border transition-colors cursor-pointer hover:border-blue-500 ${selectedJob?.jobId === jobId ? "ring-2 ring-blue-400" : ""
                }`}
              onClick={() => handleSelectJob(jobId, jobType)}
            >
              <CardHeader className="py-3 flex flex-row items-center justify-between gap-2">
                <div className="space-y-1">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <span className="capitalize">{jobType || "unknown"}</span>
                    {pinned && (
                      <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300 text-[10px] px-2 py-0.5">
                        Pinned
                      </Badge>
                    )}
                    {isCompared && (
                      <Badge className="bg-blue-100 text-blue-800 border-blue-300 text-[10px] px-2 py-0.5">
                        Comparing
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-600">
                    <span className="font-mono">{jobId}</span>
                    {job.created_at && (
                      <>
                        <span className="mx-1">•</span>
                        <span>
                          {new Date(job.created_at).toLocaleDateString()} {" "}
                          {new Date(job.created_at).toLocaleTimeString()}
                        </span>
                      </>
                    )}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={`${getStatusBadgeVariant(status)} font-semibold text-[11px] px-2 py-0.5`}>
                    {status ? status.toUpperCase() : "UNKNOWN"}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    className={`h-8 w-8 text-xs ${isCompared ? "border-blue-500 text-blue-700" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleCompareSelection(jobId);
                    }}
                    title={isCompared ? "Remove from comparison" : "Select for comparison"}
                  >
                    {isCompared ? "2" : "C"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePinToggle(jobId, pinned);
                    }}
                  >
                    {pinned ? (
                      <PinOff className="h-4 w-4" />
                    ) : (
                      <Pin className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="py-3 space-y-2">
                <div className="flex justify-between items-center text-xs text-slate-600 mb-1">
                  <span className="truncate max-w-[60%]">{modelName}</span>
                  <span>{job.progress ?? 0}%</span>
                </div>
                <Progress value={job.progress ?? 0} className="h-2" />
                {miniHeatmap}
                {status === "completed" && jobType === "xgboost" && (
                  <div className="mt-2 flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        openExplainability(jobId);
                      }}
                    >
                      Explainability
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {compareSelection.length > 0 && (
        <div className="mt-4 flex items-center justify-between text-xs text-slate-600">
          <span>
            Selected for comparison: {compareSelection.join(", ")}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCompareSelection([])}
          >
            Clear comparison
          </Button>
        </div>
      )}

      {compareSelection.length === 2 && Object.keys(compareJobs).length === 2 && (
        <div className="mt-6 border rounded-lg p-4 bg-slate-50 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800">Run Comparison</h3>
            {isLoadingCompare && (
              <span className="text-xs text-slate-500">Loading comparison...</span>
            )}
          </div>

          {(() => {
            const [idA, idB] = compareSelection;
            const jobA = compareJobs[idA];
            const jobB = compareJobs[idB];
            if (!jobA || !jobB) return null;

            const metricsA: any = jobA.metrics || {};
            const metricsB: any = jobB.metrics || {};

            const perA = metricsA.per_antibiotic_metrics || {};
            const perB = metricsB.per_antibiotic_metrics || {};
            const antibioticSet = new Set<string>([...Object.keys(perA), ...Object.keys(perB)]);
            const antibiotics = Array.from(antibioticSet).sort();

            const summaryRows = [
              {
                label: "Model type",
                a: metricsA.model_type || jobA.job_type,
                b: metricsB.model_type || jobB.job_type,
              },
              {
                label: "Model name",
                a: metricsA.model_name || jobA.metadata?.model_name || jobA.job_id,
                b: metricsB.model_name || jobB.metadata?.model_name || jobB.job_id,
              },
              {
                label: "Genomes / Genes",
                a:
                  metricsA.n_genomes !== undefined
                    ? `${metricsA.n_genomes} genomes${metricsA.n_features !== undefined ? `, ${metricsA.n_features} features` : ""
                    }`
                    : metricsA.n_genes !== undefined
                      ? `${metricsA.n_genes} genes`
                      : "N/A",
                b:
                  metricsB.n_genomes !== undefined
                    ? `${metricsB.n_genomes} genomes${metricsB.n_features !== undefined ? `, ${metricsB.n_features} features` : ""
                    }`
                    : metricsB.n_genes !== undefined
                      ? `${metricsB.n_genes} genes`
                      : "N/A",
              },
              {
                label: "Antibiotics (successful)",
                a:
                  metricsA.n_antibiotics !== undefined
                    ? `${metricsA.n_successful_models ?? "-"}/${metricsA.n_antibiotics}`
                    : "N/A",
                b:
                  metricsB.n_antibiotics !== undefined
                    ? `${metricsB.n_successful_models ?? "-"}/${metricsB.n_antibiotics}`
                    : "N/A",
              },
              {
                label: "Avg accuracy",
                a:
                  metricsA.avg_accuracy !== undefined
                    ? `${(metricsA.avg_accuracy * 100).toFixed(1)}%`
                    : "N/A",
                b:
                  metricsB.avg_accuracy !== undefined
                    ? `${(metricsB.avg_accuracy * 100).toFixed(1)}%`
                    : "N/A",
              },
              {
                label: "Avg F1 (macro)",
                a:
                  metricsA.avg_f1_macro !== undefined
                    ? `${(metricsA.avg_f1_macro * 100).toFixed(1)}%`
                    : "N/A",
                b:
                  metricsB.avg_f1_macro !== undefined
                    ? `${(metricsB.avg_f1_macro * 100).toFixed(1)}%`
                    : "N/A",
              },
              {
                label: "Avg Jaccard (macro)",
                a:
                  metricsA.avg_jaccard_macro !== undefined
                    ? `${(metricsA.avg_jaccard_macro * 100).toFixed(1)}%`
                    : "N/A",
                b:
                  metricsB.avg_jaccard_macro !== undefined
                    ? `${(metricsB.avg_jaccard_macro * 100).toFixed(1)}%`
                    : "N/A",
              },
            ];

            return (
              <>
                <div className="grid grid-cols-3 gap-2 text-xs md:text-sm">
                  <div className="font-semibold text-slate-500">Metric</div>
                  <div className="font-semibold text-slate-700 truncate">
                    {jobA.metadata?.model_name || jobA.job_id}
                  </div>
                  <div className="font-semibold text-slate-700 truncate">
                    {jobB.metadata?.model_name || jobB.job_id}
                  </div>
                  {summaryRows.map((row) => {
                    let classA = "";
                    let classB = "";

                    if (row.label === "Avg accuracy") {
                      const aNum = typeof metricsA.avg_accuracy === "number" ? metricsA.avg_accuracy : NaN;
                      const bNum = typeof metricsB.avg_accuracy === "number" ? metricsB.avg_accuracy : NaN;
                      if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
                        if (bNum > aNum) {
                          classB = "text-green-600 font-semibold";
                          classA = "text-slate-500";
                        } else if (aNum > bNum) {
                          classA = "text-green-600 font-semibold";
                          classB = "text-slate-500";
                        }
                      }
                    } else if (row.label === "Avg F1 (macro)") {
                      const aNum = typeof metricsA.avg_f1_macro === "number" ? metricsA.avg_f1_macro : NaN;
                      const bNum = typeof metricsB.avg_f1_macro === "number" ? metricsB.avg_f1_macro : NaN;
                      if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
                        if (bNum > aNum) {
                          classB = "text-green-600 font-semibold";
                          classA = "text-slate-500";
                        } else if (aNum > bNum) {
                          classA = "text-green-600 font-semibold";
                          classB = "text-slate-500";
                        }
                      }
                    } else if (row.label === "Avg Jaccard (macro)") {
                      const aNum = typeof metricsA.avg_jaccard_macro === "number" ? metricsA.avg_jaccard_macro : NaN;
                      const bNum = typeof metricsB.avg_jaccard_macro === "number" ? metricsB.avg_jaccard_macro : NaN;
                      if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
                        if (bNum > aNum) {
                          classB = "text-green-600 font-semibold";
                          classA = "text-slate-500";
                        } else if (aNum > bNum) {
                          classA = "text-green-600 font-semibold";
                          classB = "text-slate-500";
                        }
                      }
                    } else if (row.label === "Antibiotics (successful)") {
                      const aSucc = typeof metricsA.n_successful_models === "number" ? metricsA.n_successful_models : NaN;
                      const bSucc = typeof metricsB.n_successful_models === "number" ? metricsB.n_successful_models : NaN;
                      if (!Number.isNaN(aSucc) && !Number.isNaN(bSucc)) {
                        if (bSucc > aSucc) {
                          classB = "text-green-600 font-semibold";
                          classA = "text-slate-500";
                        } else if (aSucc > bSucc) {
                          classA = "text-green-600 font-semibold";
                          classB = "text-slate-500";
                        }
                      }
                    }

                    return (
                      <React.Fragment key={row.label}>
                        <div className="text-slate-500">{row.label}</div>
                        <div className={classA}>{row.a}</div>
                        <div className={classB}>{row.b}</div>
                      </React.Fragment>
                    );
                  })}
                </div>

                {antibiotics.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs md:text-sm font-semibold mb-2 text-slate-800">
                      Per-antibiotic performance
                    </h4>
                    <div className="border rounded-md overflow-auto max-h-80">
                      <table className="min-w-full text-xs">
                        <thead className="bg-slate-100">
                          <tr>
                            <th className="px-2 py-1 text-left">Antibiotic</th>
                            <th className="px-2 py-1 text-right">
                              Acc A
                            </th>
                            <th className="px-2 py-1 text-right">
                              Acc B
                            </th>
                            <th className="px-2 py-1 text-right">
                              F1 A
                            </th>
                            <th className="px-2 py-1 text-right">
                              F1 B
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {antibiotics.map((ab) => {
                            const mA: any = perA[ab] || {};
                            const mB: any = perB[ab] || {};
                            const accA = typeof mA.accuracy === "number" ? mA.accuracy * 100 : NaN;
                            const accB = typeof mB.accuracy === "number" ? mB.accuracy * 100 : NaN;
                            const f1A = typeof mA.f1_macro === "number" ? mA.f1_macro * 100 : NaN;
                            const f1B = typeof mB.f1_macro === "number" ? mB.f1_macro * 100 : NaN;
                            const accAClass =
                              !Number.isNaN(accA) && !Number.isNaN(accB) && accA > accB
                                ? "text-green-600 font-semibold"
                                : "";
                            const accBClass =
                              !Number.isNaN(accA) && !Number.isNaN(accB) && accB > accA
                                ? "text-green-600 font-semibold"
                                : "";
                            const f1AClass =
                              !Number.isNaN(f1A) && !Number.isNaN(f1B) && f1A > f1B
                                ? "text-green-600 font-semibold"
                                : "";
                            const f1BClass =
                              !Number.isNaN(f1A) && !Number.isNaN(f1B) && f1B > f1A
                                ? "text-green-600 font-semibold"
                                : "";
                            return (
                              <tr key={ab} className="odd:bg-white even:bg-slate-50">
                                <td className="px-2 py-1 text-left capitalize">
                                  {ab}
                                </td>
                                <td className={`px-2 py-1 text-right ${accAClass}`}>
                                  {Number.isNaN(accA) ? "-" : `${accA.toFixed(1)}%`}
                                </td>
                                <td className={`px-2 py-1 text-right ${accBClass}`}>
                                  {Number.isNaN(accB) ? "-" : `${accB.toFixed(1)}%`}
                                </td>
                                <td className={`px-2 py-1 text-right ${f1AClass}`}>
                                  {Number.isNaN(f1A) ? "-" : `${f1A.toFixed(1)}%`}
                                </td>
                                <td className={`px-2 py-1 text-right ${f1BClass}`}>
                                  {Number.isNaN(f1B) ? "-" : `${f1B.toFixed(1)}%`}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export default TrainingHistory;
