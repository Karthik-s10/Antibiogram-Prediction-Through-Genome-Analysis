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

