import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  Download,
  RefreshCw,
  TrendingUp,
  BarChart3,
  X,
} from "lucide-react";
import { getJobStatus, cancelJob, type JobStatus } from "@/services/apiClient";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface TrainingStatusProps {
  jobId: string;
  modelType: string;
  onComplete?: () => void;
  onNewTraining?: () => void;
}

const TrainingStatus = ({ jobId, modelType, onComplete, onNewTraining }: TrainingStatusProps) => {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);

  useEffect(() => {
    if (!jobId || !isPolling) return;

    const pollStatus = async () => {
      try {
        const jobStatus = await getJobStatus(jobId);
        setStatus(jobStatus);
        setError(null);

        // Stop polling if job is completed, failed, or cancelled
        if (jobStatus.status === "completed" || jobStatus.status === "failed" || jobStatus.status === "cancelled") {
          setIsPolling(false);
          if (jobStatus.status === "completed" && onComplete) {
            onComplete();
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch job status");
        setIsPolling(false);
      }
    };

    // Initial fetch
    pollStatus();

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [jobId, isPolling, onComplete]);

  const getStatusIcon = () => {
    if (!status) return <Loader2 className="h-6 w-6 animate-spin text-blue-600" />;

    switch (status.status) {
      case "completed":
        return <CheckCircle className="h-6 w-6 text-green-600" />;
      case "failed":
        return <XCircle className="h-6 w-6 text-red-600" />;
      case "running":
        return <Loader2 className="h-6 w-6 animate-spin text-blue-600" />;
      case "cancelled":
        return <XCircle className="h-6 w-6 text-orange-600" />;
      default:
        return <Clock className="h-6 w-6 text-gray-600" />;
    }
  };

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this training job?")) {
      return;
    }
    
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
      // Status will update on next poll
      setTimeout(() => {
        const pollStatus = async () => {
          try {
            const jobStatus = await getJobStatus(jobId);
            setStatus(jobStatus);
            if (jobStatus.status === "cancelled") {
              setIsPolling(false);
            }
          } catch (err) {
            console.error("Error polling after cancel:", err);
          }
        };
        pollStatus();
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Failed to cancel job");
    } finally {
      setIsCancelling(false);
    }
  };

  const getStatusColor = () => {
    if (!status) return "bg-gray-100 text-gray-800";

    switch (status.status) {
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

  return (
    <div className="w-full max-w-5xl mx-auto space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="flex items-center gap-2">
                {getStatusIcon()}
                Training Job Status
              </CardTitle>
              <CardDescription className="mt-2">
                Job ID: <code className="text-xs bg-gray-100 px-2 py-1 rounded">{jobId}</code>
              </CardDescription>
            </div>
            <Badge className={`${getStatusColor()} font-semibold text-sm px-3 py-1`}>
              {status?.status.toUpperCase() || "LOADING"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Progress Bar */}
          {status && status.status !== "failed" && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{status.current_step}</span>
                <span className="text-gray-600">{status.progress}%</span>
              </div>
              <Progress value={status.progress} className="h-3" />
            </div>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Job Error */}
          {status?.error && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Training Failed</AlertTitle>
              <AlertDescription className="whitespace-pre-wrap">
                {status.error}
              </AlertDescription>
            </Alert>
          )}

          {/* Metadata */}
          {status && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-xs text-gray-600">Model Type</p>
                <p className="font-semibold capitalize">{status.job_type}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Model Name</p>
                <p className="font-semibold">{status.metadata.model_name || "N/A"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Started</p>
                <p className="font-semibold">
                  {new Date(status.created_at).toLocaleTimeString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Duration</p>
                <p className="font-semibold">
                  {status.completed_at
                    ? `${Math.round(
                        (new Date(status.completed_at).getTime() -
                          new Date(status.created_at).getTime()) /
                          1000
                      )}s`
                    : "In progress..."}
                </p>
              </div>
            </div>
          )}

          {/* Metrics Display (when completed) */}
          {status?.status === "completed" && status.metrics && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-lg font-semibold">
                <TrendingUp className="h-5 w-5 text-green-600" />
                Training Results
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-4">
                  <p className="text-xs text-gray-600">Avg Accuracy</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(status.metrics.avg_accuracy * 100).toFixed(1)}%
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-gray-600">Avg F1 Score</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {(status.metrics.avg_f1_macro * 100).toFixed(1)}%
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-gray-600">Avg Jaccard Score</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {(status.metrics.avg_jaccard_macro * 100).toFixed(1)}%
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-gray-600">Models Trained</p>
                  <p className="text-2xl font-bold text-orange-600">
                    {status.metrics.n_successful_models}/{status.metrics.n_antibiotics}
                  </p>
                </Card>
              </div>

              {/* Detailed per-antibiotic visuals: heatmap + per-class F1 line chart */}
              {status.metrics.per_antibiotic_metrics && (() => {
                const perMetrics: any = status.metrics.per_antibiotic_metrics;
                const antibiotics = Object.keys(perMetrics).sort();
                if (antibiotics.length === 0) return null;

                const classDefs = [
                  { key: "0", label: "S", name: "Susceptible", rgb: "34,197,94", colorClass: "text-emerald-400" },
                  { key: "1", label: "I", name: "Intermediate", rgb: "245,158,11", colorClass: "text-amber-400" },
                  { key: "2", label: "R", name: "Resistant", rgb: "239,68,68", colorClass: "text-rose-400" },
                ];

                let maxSupport = 0;
                let maxF1 = 0;

                antibiotics.forEach((ab) => {
                  const m = perMetrics[ab] || {};
                  const perClass = m.per_class || {};
                  classDefs.forEach(({ key }) => {
                    const cls = perClass[key] || {};
                    const support = typeof cls["support"] === "number" ? cls["support"] : 0;
                    const f1 = typeof cls["f1-score"] === "number" ? cls["f1-score"] : 0;
                    if (support > maxSupport) maxSupport = support;
                    if (f1 > maxF1) maxF1 = f1;
                  });
                });

                if (maxSupport <= 0) maxSupport = 1;
                if (maxF1 <= 0) maxF1 = 1;

                const width = Math.max(antibiotics.length * 30 + 80, 360);
                const height = 220;
                const marginLeft = 50;
                const marginRight = 16;
                const marginTop = 24;
                const marginBottom = 40;
                const plotWidth = width - marginLeft - marginRight;
                const plotHeight = height - marginTop - marginBottom;
                const stepX = antibiotics.length > 1 ? plotWidth / (antibiotics.length - 1) : 0;

                const buildLinePoints = (classKey: string) => {
                  const pts: string[] = [];
                  antibiotics.forEach((ab, idx) => {
                    const m = perMetrics[ab] || {};
                    const perClass = m.per_class || {};
                    const cls = perClass[classKey] || {};
                    const vRaw = typeof cls["f1-score"] === "number" ? cls["f1-score"] : 0;
                    const v = Math.max(0, vRaw);
                    const x = marginLeft + (antibiotics.length > 1 ? idx * stepX : plotWidth / 2);
                    const y = marginTop + (1 - v / maxF1) * plotHeight;
                    pts.push(`${x},${y}`);
                  });
                  return pts.join(" ");
                };

                return (
                  <div className="space-y-6 mt-4">
                    {/* Class distribution heatmap */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <BarChart3 className="h-5 w-5 text-slate-700" />
                          <h3 className="font-semibold text-sm">Class Distribution Heatmap (per antibiotic)</h3>
                        </div>
                        <div className="flex gap-3 text-[11px] text-slate-500">
                          {classDefs.map((c) => (
                            <span key={c.key} className="flex items-center gap-1">
                              <span
                                className="inline-block w-3 h-3 rounded-sm"
                                style={{ backgroundColor: `rgb(${c.rgb})` }}
                              />
                              <span className={c.colorClass}>{c.label}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="border rounded-lg bg-slate-950/95 text-xs text-slate-100 overflow-auto">
                        <div
                          className="grid min-w-full"
                          style={{
                            gridTemplateColumns: `80px repeat(${antibiotics.length}, minmax(28px,1fr))`,
                          }}
                        >
                          {/* Header row */}
                          <div className="border-b border-slate-800 bg-slate-900/80 flex items-center justify-center text-[10px] uppercase tracking-wide">
                            Class
                          </div>
                          {antibiotics.map((ab) => (
                            <div
                              key={`header-${ab}`}
                              className="border-b border-slate-800 bg-slate-900/80 px-2 py-1 text-[10px] text-center truncate"
                              title={ab}
                            >
                              {ab}
                            </div>
                          ))}

                          {/* Rows: S/I/R */}
                          {classDefs.map((cls) => (
                            <React.Fragment key={cls.key}>
                              <div className="border-b border-slate-800 bg-slate-900/70 px-2 py-1 flex items-center gap-2">
                                <span className={`text-[11px] font-semibold ${cls.colorClass}`}>{cls.label}</span>
                                <span className="text-[10px] text-slate-400 truncate">{cls.name}</span>
                              </div>
                              {antibiotics.map((ab) => {
                                const m = perMetrics[ab] || {};
                                const perClass = m.per_class || {};
                                const cData = perClass[cls.key] || {};
                                const support =
                                  typeof cData["support"] === "number" ? (cData["support"] as number) : 0;
                                const intensity = maxSupport > 0 ? support / maxSupport : 0;
                                const alpha = 0.12 + 0.78 * intensity;
                                const bgColor = `rgba(${cls.rgb}, ${alpha.toFixed(3)})`;
                                return (
                                  <div
                                    key={`${cls.key}-${ab}`}
                                    className="border-b border-slate-900/60 border-r border-slate-900/40 h-7 flex items-center justify-center text-[10px]"
                                    style={{ backgroundColor: bgColor }}
                                    title={`${ab} · ${cls.name} · samples=${support}`}
                                  >
                                    {support > 0 ? support : ""}
                                  </div>
                                );
                              })}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Per-class F1 line chart */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="h-5 w-5 text-slate-700" />
                          <h3 className="font-semibold text-sm">Per-class F1 by antibiotic</h3>
                        </div>
                        <div className="flex gap-3 text-[11px] text-slate-500">
                          <span className="flex items-center gap-1">
                            <span className="inline-block w-4 h-0.5 rounded-full bg-emerald-400" /> S
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="inline-block w-4 h-0.5 rounded-full bg-amber-400" /> I
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="inline-block w-4 h-0.5 rounded-full bg-rose-400" /> R
                          </span>
                        </div>
                      </div>
                      <div className="bg-slate-950/95 border border-slate-800 rounded-lg p-3">
                        <svg
                          viewBox={`0 0 ${width} ${height}`}
                          className="w-full h-56 text-[10px] text-slate-400"
                        >
                          {/* Y-axis grid lines */}
                          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
                            const y = marginTop + (1 - t) * plotHeight;
                            return (
                              <g key={`grid-${t}`}>
                                <line
                                  x1={marginLeft}
                                  x2={width - marginRight}
                                  y1={y}
                                  y2={y}
                                  stroke="rgba(148, 163, 184, 0.3)"
                                  strokeWidth={0.5}
                                  strokeDasharray="2 3"
                                />
                                <text x={8} y={y + 3} fill="#94a3b8">
                                  {(t * maxF1).toFixed(2)}
                                </text>
                              </g>
                            );
                          })}

                          {/* X-axis antibiotic labels */}
                          {antibiotics.map((ab, idx) => {
                            const x = marginLeft + (antibiotics.length > 1 ? idx * stepX : plotWidth / 2);
                            return (
                              <g key={`x-${ab}`}>
                                <line
                                  x1={x}
                                  x2={x}
                                  y1={marginTop + plotHeight}
                                  y2={marginTop + plotHeight + 4}
                                  stroke="#64748b"
                                  strokeWidth={0.5}
                                />
                                <text
                                  x={x}
                                  y={height - 4}
                                  textAnchor="middle"
                                  fill="#94a3b8"
                                  transform={`rotate(-35 ${x} ${height - 4})`}
                                >
                                  {ab}
                                </text>
                              </g>
                            );
                          })}

                          {/* Lines per class */}
                          <polyline
                            points={buildLinePoints("0")}
                            fill="none"
                            stroke="#22c55e"
                            strokeWidth={2}
                          />
                          <polyline
                            points={buildLinePoints("1")}
                            fill="none"
                            stroke="#fbbf24"
                            strokeWidth={2}
                          />
                          <polyline
                            points={buildLinePoints("2")}
                            fill="none"
                            stroke="#fb7185"
                            strokeWidth={2}
                          />

                          {/* Points */}
                          {classDefs.map((cls) => (
                            <React.Fragment key={`pts-${cls.key}`}>
                              {antibiotics.map((ab, idx) => {
                                const m = perMetrics[ab] || {};
                                const perClass = m.per_class || {};
                                const cData = perClass[cls.key] || {};
                                const vRaw =
                                  typeof cData["f1-score"] === "number" ? (cData["f1-score"] as number) : 0;
                                const v = Math.max(0, vRaw);
                                const x = marginLeft + (antibiotics.length > 1 ? idx * stepX : plotWidth / 2);
                                const y = marginTop + (1 - v / maxF1) * plotHeight;
                                return (
                                  <circle
                                    key={`${cls.key}-${ab}`}
                                    cx={x}
                                    cy={y}
                                    r={2.5}
                                    fill={
                                      cls.key === "0"
                                        ? "#22c55e"
                                        : cls.key === "1"
                                        ? "#fbbf24"
                                        : "#fb7185"
                                    }
                                  />
                                );
                              })}
                            </React.Fragment>
                          ))}
                        </svg>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {status.metrics.per_antibiotic_metrics && (
                <div className="space-y-3 mt-4">
                  <div className="flex items-center gap-2 mb-1">
                    <BarChart3 className="h-5 w-5" />
                    <h3 className="font-semibold text-sm">Performance Overview (per antibiotic)</h3>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-auto pr-1">
                    {Object.entries(status.metrics.per_antibiotic_metrics).map(
                      ([antibiotic, metrics]: [string, any]) => {
                        if (metrics.error) return null;
                        const acc = typeof metrics.accuracy === "number" ? metrics.accuracy * 100 : 0;
                        const f1 = typeof metrics.f1_macro === "number" ? metrics.f1_macro * 100 : 0;
                        const maxBar = Math.max(acc, f1, 1);
                        const accWidth = (acc / maxBar) * 100;
                        const f1Width = (f1 / maxBar) * 100;
                        return (
                          <div key={`${antibiotic}-chart`} className="space-y-1">
                            <div className="flex justify-between text-xs text-slate-700">
                              <span className="font-medium capitalize truncate max-w-[50%]">
                                {antibiotic}
                              </span>
                              <span className="text-[11px] text-slate-500">
                                Acc {(acc || 0).toFixed(1)}% · F1 {(f1 || 0).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex gap-1 items-center">
                              <div className="flex-1 h-2 rounded bg-slate-200 overflow-hidden">
                                <div
                                  className="h-2 bg-green-500"
                                  style={{ width: `${accWidth}%` }}
                                />
                              </div>
                              <div className="flex-1 h-2 rounded bg-slate-200 overflow-hidden">
                                <div
                                  className="h-2 bg-blue-500"
                                  style={{ width: `${f1Width}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              )}

              {/* Per-Antibiotic Metrics Table */}
              {status.metrics.per_antibiotic_metrics && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <BarChart3 className="h-5 w-5" />
                    <h3 className="font-semibold">Per-Antibiotic Performance</h3>
                  </div>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Antibiotic</TableHead>
                          <TableHead className="text-right">Accuracy</TableHead>
                          <TableHead className="text-right">F1 Score</TableHead>
                          <TableHead className="text-right">Jaccard</TableHead>
                          <TableHead className="text-right">Samples</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(status.metrics.per_antibiotic_metrics).map(
                          ([antibiotic, metrics]: [string, any]) => (
                            <TableRow key={antibiotic}>
                              <TableCell className="font-medium capitalize">
                                {antibiotic}
                              </TableCell>
                              <TableCell className="text-right">
                                {metrics.error ? (
                                  <span className="text-red-500 text-xs">{metrics.error}</span>
                                ) : (
                                  <span className="text-green-600 font-semibold">
                                    {(metrics.accuracy * 100).toFixed(1)}%
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-right">
                                {metrics.f1_macro && (
                                  <span className="text-blue-600 font-semibold">
                                    {(metrics.f1_macro * 100).toFixed(1)}%
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-right">
                                {metrics.jaccard_macro && (
                                  <span className="text-purple-600 font-semibold">
                                    {(metrics.jaccard_macro * 100).toFixed(1)}%
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-right text-gray-600">
                                {metrics.n_train + metrics.n_test || 0}
                              </TableCell>
                            </TableRow>
                          )
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            {(status?.status === "running" || status?.status === "pending") && (
              <Button
                variant="destructive"
                className="flex-1"
                onClick={handleCancel}
                disabled={isCancelling}
              >
                {isCancelling ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Cancelling...
                  </>
                ) : (
                  <>
                    <X className="mr-2 h-4 w-4" />
                    Cancel Training
                  </>
                )}
              </Button>
            )}
            {status?.status === "completed" && (
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => {
                  // TODO: Implement model download
                  alert("Model download coming soon!");
                }}
              >
                <Download className="mr-2 h-4 w-4" />
                Download Model
              </Button>
            )}
            {(status?.status === "completed" || status?.status === "failed" || status?.status === "cancelled") && (
              <Button
                variant="default"
                className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600"
                onClick={onNewTraining}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Train Another Model
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TrainingStatus;

