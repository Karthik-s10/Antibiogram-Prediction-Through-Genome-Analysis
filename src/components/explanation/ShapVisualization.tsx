import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  InfoIcon, RefreshCwIcon, TrendingUpIcon, TrendingDownIcon,
  SearchIcon, ChevronUpIcon, ChevronDownIcon, BarChart2Icon
} from "lucide-react";

interface ShapVisualizationProps {
  explanation: {
    shap_values: number[] | number[][];
    feature_names: string[];
    class_names?: string[];
    base_values: number | number[];
    prediction: string;
    probability?: number;
    model_type: string;
    antibiotic: string;
    force_plot_data?: any;
    waterfall_plot_data?: any;
    metadata?: any;
  };
  isLoading?: boolean;
  onRefresh?: () => void;
}

// Map letter prediction to display
const PRED_LABEL: Record<string, { label: string; color: string; bgColor: string }> = {
  R: { label: 'Resistant', color: 'text-red-700', bgColor: 'bg-red-100 border-red-300' },
  I: { label: 'Intermediate', color: 'text-amber-700', bgColor: 'bg-amber-100 border-amber-300' },
  S: { label: 'Susceptible', color: 'text-green-700', bgColor: 'bg-green-100 border-green-300' },
};

export function ShapVisualization({ explanation, isLoading = false, onRefresh }: ShapVisualizationProps) {
  const [topFeatures, setTopFeatures] = useState(20);
  const [search, setSearch] = useState('');
  const [sortByAbs, setSortByAbs] = useState(true);

  if (!explanation || !explanation.shap_values || !explanation.feature_names) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-gray-400">
            <BarChart2Icon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p className="font-medium">No SHAP data available</p>
            <p className="text-sm mt-1">Generate model explanations to see feature importance</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Normalise SHAP values ──────────────────────────────────────────────────
  let shapValues: number[];
  if (Array.isArray(explanation.shap_values[0])) {
    // multi-class: pick the R class slice if available, else first
    const sv = explanation.shap_values as number[][];
    const classIdx = explanation.class_names
      ? Math.max(explanation.class_names.indexOf(explanation.prediction), 0)
      : sv.length - 1;
    shapValues = sv[classIdx] ?? sv[0];
  } else {
    shapValues = explanation.shap_values as number[];
  }

  const baseValue = Array.isArray(explanation.base_values)
    ? explanation.base_values[0]
    : (explanation.base_values ?? 0);

  const predMeta = PRED_LABEL[explanation.prediction] ?? {
    label: explanation.prediction, color: 'text-gray-700', bgColor: 'bg-gray-100 border-gray-300'
  };

  // ── Feature list ───────────────────────────────────────────────────────────
  const allFeatures = useMemo(() => {
    return explanation.feature_names.map((f, i) => ({
      feature: f,
      value: shapValues[i] ?? 0,
      absValue: Math.abs(shapValues[i] ?? 0),
      sign: (shapValues[i] ?? 0) >= 0 ? 'positive' : 'negative' as 'positive' | 'negative',
    }));
  }, [explanation.feature_names, shapValues]);

  const sortedAll = useMemo(
    () => sortByAbs
      ? [...allFeatures].sort((a, b) => b.absValue - a.absValue)
      : [...allFeatures].sort((a, b) => b.value - a.value),
    [allFeatures, sortByAbs]
  );

  const topData = useMemo(() => sortedAll.slice(0, topFeatures), [sortedAll, topFeatures]);

  const filteredSearch = useMemo(() => {
    if (!search) return sortedAll.slice(0, 100);
    return sortedAll.filter(f => f.feature.toLowerCase().includes(search.toLowerCase())).slice(0, 100);
  }, [sortedAll, search]);

  const maxValue = useMemo(() => Math.max(...topData.map(d => d.absValue), 1e-9), [topData]);

  // ── Summary stats ──────────────────────────────────────────────────────────
  const posSum = allFeatures.filter(f => f.value > 0).reduce((s, f) => s + f.value, 0);
  const negSum = allFeatures.filter(f => f.value < 0).reduce((s, f) => s + f.value, 0);
  const finalScore = baseValue + posSum + negSum;

  const getDisplayName = (feature: string) => {
    if (feature.startsWith('kmer_')) return `k-mer: ${feature.slice(5)}`;
    if (feature.startsWith('token_')) {
      const parts = feature.split('_');
      return `Token ${parts[1]}: ${parts.slice(2).join('_')}`;
    }
    return feature;
  };

  return (
    <Card className="w-full border shadow-sm">
      {/* ── Header ── */}
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start flex-wrap gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              SHAP Feature Importance
              <Badge variant="outline" className="font-mono text-xs">{explanation.model_type}</Badge>
              <Badge variant="secondary" className="text-xs">{explanation.antibiotic}</Badge>
            </CardTitle>
            <CardDescription className="mt-0.5">
              SHAP values show how each feature drives the final prediction away from the baseline.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
            <RefreshCwIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Prediction banner */}
        <div className={`mt-3 rounded-xl border px-4 py-3 flex flex-wrap items-center gap-4 ${predMeta.bgColor}`}>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Prediction</p>
            <p className={`text-2xl font-bold ${predMeta.color}`}>
              {predMeta.label}
              <span className="text-base font-normal ml-1">({explanation.prediction})</span>
            </p>
          </div>
          {explanation.probability != null && (
            <div className="flex-1 min-w-[140px]">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <Progress value={explanation.probability * 100} className="h-2 flex-1" />
                <span className={`text-sm font-bold font-mono ${predMeta.color}`}>
                  {(explanation.probability * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          )}
          <div className="text-xs text-gray-600 space-y-0.5">
            <p>Baseline: <span className="font-mono font-medium">{baseValue.toFixed(4)}</span></p>
            <p>+Impact: <span className="font-mono text-red-600">+{posSum.toFixed(4)}</span></p>
            <p>−Impact: <span className="font-mono text-green-600">{negSum.toFixed(4)}</span></p>
            <p>Final score: <span className="font-mono font-bold">{finalScore.toFixed(4)}</span></p>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="chart" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="chart">Bar Chart</TabsTrigger>
            <TabsTrigger value="table">Feature Table</TabsTrigger>
            <TabsTrigger value="details">Model Details</TabsTrigger>
          </TabsList>

          {/* ══ BAR CHART TAB ══ */}
          <TabsContent value="chart" className="space-y-4">
            {/* Controls */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-600">Show top</span>
                <select
                  value={topFeatures}
                  onChange={e => setTopFeatures(Number(e.target.value))}
                  className="border rounded px-2 py-1 text-sm bg-white shadow-sm"
                >
                  {[10, 15, 20, 30, 50].map(n => (
                    <option key={n} value={n}>Top {n}</option>
                  ))}
                </select>
              </div>
              <Button
                variant="outline" size="sm"
                onClick={() => setSortByAbs(!sortByAbs)}
                className="text-xs"
              >
                Sort: {sortByAbs ? 'Absolute impact' : 'Signed value'}
                {sortByAbs ? <ChevronDownIcon className="ml-1 h-3 w-3" /> : <ChevronUpIcon className="ml-1 h-3 w-3" />}
              </Button>
            </div>

            {/* Legend */}
            <div className="flex gap-4 text-xs text-gray-600">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-red-400" />
                <span>Increases resistance risk</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-emerald-400" />
                <span>Decreases resistance risk</span>
              </div>
            </div>

            {/* Centered diverging bars */}
            <div className="space-y-2">
              {topData.map((item, idx) => {
                const pct = (item.absValue / maxValue) * 50; // max 50% from center
                return (
                  <TooltipProvider key={idx}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-2 group cursor-default">
                          {/* rank */}
                          <span className="text-xs text-gray-400 w-4 text-right flex-shrink-0">{idx + 1}</span>
                          {/* label */}
                          <span className="text-xs font-medium w-36 truncate flex-shrink-0 text-right text-gray-700" title={item.feature}>
                            {getDisplayName(item.feature)}
                          </span>
                          {/* dual-sided bar */}
                          <div className="flex-1 flex items-center h-5 relative">
                            {/* center line */}
                            <div className="absolute inset-y-0 left-1/2 w-px bg-gray-300 z-10" />
                            {item.sign === 'negative' ? (
                              <div className="flex-1 flex justify-center">
                                <div
                                  className="h-4 rounded-l bg-emerald-400 transition-all duration-300 ml-0"
                                  style={{ width: `${pct}%`, marginLeft: `${50 - pct}%` }}
                                />
                                <div style={{ width: '50%' }} />
                              </div>
                            ) : (
                              <div className="flex-1 flex justify-center">
                                <div style={{ width: '50%' }} />
                                <div
                                  className="h-4 rounded-r bg-red-400 transition-all duration-300"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            )}
                          </div>
                          {/* value + icon */}
                          <div className="flex items-center gap-1 flex-shrink-0 w-20 justify-end">
                            {item.sign === 'positive'
                              ? <TrendingUpIcon className="h-3 w-3 text-red-500" />
                              : <TrendingDownIcon className="h-3 w-3 text-emerald-500" />}
                            <span className={`text-xs font-mono tabular-nums ${item.sign === 'positive' ? 'text-red-600' : 'text-emerald-600'}`}>
                              {item.sign === 'positive' ? '+' : ''}{item.value.toFixed(4)}
                            </span>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-xs text-xs">
                        <p className="font-semibold break-all">{item.feature}</p>
                        <p>SHAP: <span className="font-mono">{item.value.toFixed(6)}</span></p>
                        <p>|SHAP|: <span className="font-mono">{item.absValue.toFixed(6)}</span></p>
                        <p className="mt-1 text-gray-400">
                          {item.sign === 'positive'
                            ? '↑ Pushes prediction toward RESISTANCE'
                            : '↓ Pushes prediction toward SUSCEPTIBILITY'}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                );
              })}
            </div>

            {/* Summary mini stats */}
            <div className="mt-4 grid grid-cols-3 gap-3 text-center text-sm border-t pt-4">
              <div className="bg-gray-50 rounded-lg p-2">
                <p className="text-xs text-gray-500">Total features</p>
                <p className="font-bold font-mono">{allFeatures.length.toLocaleString()}</p>
              </div>
              <div className="bg-red-50 rounded-lg p-2">
                <p className="text-xs text-red-500">Resistance drivers</p>
                <p className="font-bold font-mono text-red-700">
                  {allFeatures.filter(f => f.value > 0).length.toLocaleString()}
                </p>
              </div>
              <div className="bg-emerald-50 rounded-lg p-2">
                <p className="text-xs text-emerald-600">Susceptibility drivers</p>
                <p className="font-bold font-mono text-emerald-700">
                  {allFeatures.filter(f => f.value < 0).length.toLocaleString()}
                </p>
              </div>
            </div>
          </TabsContent>

          {/* ══ TABLE TAB ══ */}
          <TabsContent value="table" className="space-y-3">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search features…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>
            <div className="rounded-lg border overflow-auto max-h-[480px]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-gray-600">#</th>
                    <th className="text-left px-3 py-2 font-semibold text-gray-600">Feature</th>
                    <th className="text-right px-3 py-2 font-semibold text-gray-600">SHAP value</th>
                    <th className="text-right px-3 py-2 font-semibold text-gray-600">|SHAP|</th>
                    <th className="text-center px-3 py-2 font-semibold text-gray-600">Direction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredSearch.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-3 py-1.5 text-gray-400">{idx + 1}</td>
                      <td className="px-3 py-1.5 font-mono max-w-[220px] truncate" title={item.feature}>
                        {item.feature}
                      </td>
                      <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${item.sign === 'positive' ? 'text-red-600' : 'text-emerald-600'}`}>
                        {item.sign === 'positive' ? '+' : ''}{item.value.toFixed(6)}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono tabular-nums text-gray-700">
                        {item.absValue.toFixed(6)}
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        {item.sign === 'positive'
                          ? <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0">↑ R</Badge>
                          : <Badge className="bg-emerald-100 text-emerald-700 text-[10px] px-1.5 py-0">↓ S</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredSearch.length === 0 && (
                <p className="text-center text-gray-400 py-8 text-sm">No features found</p>
              )}
            </div>
          </TabsContent>

          {/* ══ DETAILS TAB ══ */}
          <TabsContent value="details" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">Prediction Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Model type</span>
                    <Badge>{explanation.model_type}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Antibiotic</span>
                    <Badge variant="secondary">{explanation.antibiotic}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Prediction</span>
                    <span className={`font-bold ${predMeta.color}`}>{predMeta.label} ({explanation.prediction})</span>
                  </div>
                  {explanation.probability != null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Confidence</span>
                      <div className="flex items-center gap-2">
                        <Progress value={explanation.probability * 100} className="w-20 h-1.5" />
                        <span className="font-mono text-xs">{(explanation.probability * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">SHAP Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  {[
                    ['Total features', allFeatures.length.toLocaleString()],
                    ['SHAP values computed', shapValues.length.toLocaleString()],
                    ['Baseline (f₀)', baseValue.toFixed(6)],
                    ['Max positive SHAP', Math.max(...allFeatures.filter(f => f.value > 0).map(f => f.value), 0).toFixed(6)],
                    ['Max negative SHAP', Math.min(...allFeatures.filter(f => f.value < 0).map(f => f.value), 0).toFixed(6)],
                    ['Net effect (Σ SHAP)', (posSum + negSum).toFixed(6)],
                    ['Final score', finalScore.toFixed(6)],
                  ].map(([label, val]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-gray-500">{label}</span>
                      <span className="font-mono text-xs">{val}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            {explanation.metadata && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">Technical Metadata</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs">
                    {Object.entries(explanation.metadata).filter(([, v]) => typeof v !== 'object').map(([k, v]) => (
                      <div key={k} className="flex justify-between py-1 border-b border-gray-50">
                        <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}</span>
                        <span className="font-mono text-gray-700">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
