/**
 * API Client for communicating with the FastAPI backend.
 * Provides typed methods for training, prediction, and status endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface TrainingJobResponse {
  job_id: string;
  status: string;
  message: string;
  model_name: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step: string;
  job_type: string;
  pinned?: boolean;
  metadata: Record<string, any>;
  metrics?: Record<string, any>;
  error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface PredictionResponse {
  status: string;
  genome_name: string;
  model_type?: string;
  models_used?: {
    xgboost?: any;
    transformer?: any;
  };
  predictions: Array<{
    antibiotic: string;
    prediction: 'S' | 'I' | 'R';
    confidence: number;
    class_probabilities?: {
      S: number;
      I: number;
      R: number;
    };
    xgboost_markers?: Array<{
      kmer: string;
      importance: number;
      normalized_importance?: number;
      count?: number;
    }>;
    transformer_markers?: Array<{
      gene_index: number;
      class_index: number;
      class_label: 'S' | 'I' | 'R' | 'Unknown';
      importance?: number;
      normalized_importance?: number;
      best_hit_title?: string;
      best_hit_id?: string;
      best_hit_identity?: number | null;
    }>;
  }>;
  analysis_summary?: {
    sequence_length: number;
    gc_content: number;
    unique_kmers_found: number;
    model_used: string;
    n_antibiotics: number;
    similar_genomes?: Array<{
      genome_id: string;
      species: string;
      similarity_score: number;
      organism_name?: string | null;
      genome_name?: string | null;
      strain?: string | null;
    }>;
    n_genes?: number | null;
    similarity_search_performed?: boolean;
    similarity_search_required?: boolean;
    ensemble_details?: any;
  };
}

/**
 * Train an XGBoost model
 */
export async function trainXGBoost(
  kmerFile: File,
  phenotypeFile: File,
  options?: {
    model_name?: string;
    max_depth?: number;
    learning_rate?: number;
    n_estimators?: number;
    k?: number;
    rosetta_file?: File;
    use_rosetta_preprocessor?: boolean;
    max_genomes?: number;
    cycle_index?: number;
  }
): Promise<TrainingJobResponse> {
  const formData = new FormData();
  formData.append('kmer_file', kmerFile);
  formData.append('phenotype_file', phenotypeFile);
  
  if (options?.model_name) formData.append('model_name', options.model_name);
  if (options?.max_depth) formData.append('max_depth', options.max_depth.toString());
  if (options?.learning_rate) formData.append('learning_rate', options.learning_rate.toString());
  if (options?.n_estimators) formData.append('n_estimators', options.n_estimators.toString());
  if (options?.k) formData.append('k', options.k.toString());
  if (options?.rosetta_file) formData.append('rosetta_file', options.rosetta_file);
  if (options?.use_rosetta_preprocessor !== undefined) {
    formData.append('use_rosetta_preprocessor', String(options.use_rosetta_preprocessor));
  }
  if (options?.max_genomes !== undefined) {
    formData.append('max_genomes', options.max_genomes.toString());
  }
  if (options?.cycle_index !== undefined) {
    formData.append('cycle_index', options.cycle_index.toString());
  }
  
  const response = await fetch(`${API_BASE_URL}/api/train/xgboost`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Training request failed' }));
    throw new Error(error.detail || 'Training request failed');
  }
  
  return response.json();
}

/**
 * Fetch XGBoost explainability report for a given model name
 */
export async function getXGBoostExplainability(modelName: string): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/api/predict/xgboost_explainability/${encodeURIComponent(modelName)}`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch explainability report' }));
    throw new Error(error.detail || 'Failed to fetch explainability report');
  }

  return response.json();
}

/**
 * Get SHAP explanation for a single prediction
 */
export async function getShapExplanation(
  antibiotic: string,
  modelType: 'xgboost' | 'transformer',
  prediction: string,
  probability: number,
  sequence?: string,
  features?: number[]
): Promise<any> {
  const payload: any = {
    antibiotic,
    model_type: modelType,
    prediction,
    probability
  };
  
  if (sequence) payload.sequence = sequence;
  if (features) payload.features = features;

  const response = await fetch(`${API_BASE_URL}/api/explanations/single`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch SHAP explanation' }));
    throw new Error(error.detail || 'Failed to fetch SHAP explanation');
  }

  return response.json();
}

/**
 * Run BLAST for a list of k-mers (best-effort, requires Biopython on backend)
 */
export async function blastKmers(
  kmers: string[],
  maxHits: number = 1,
): Promise<{ kmers: Record<string, any[]> }> {
  const response = await fetch(`${API_BASE_URL}/api/predict/xgboost_blast_kmers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kmers, max_hits: maxHits }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'BLAST request failed' }));
    throw new Error(error.detail || 'BLAST request failed');
  }

  return response.json();
}

/**
 * Pin a training job
 */
export async function pinJob(jobId: string): Promise<{ job_id: string; pinned: boolean; status?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}/pin`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to pin job' }));
    throw new Error(error.detail || 'Failed to pin job');
  }

  return response.json();
}

/**
 * Unpin a training job
 */
export async function unpinJob(jobId: string): Promise<{ job_id: string; pinned: boolean; status?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}/unpin`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to unpin job' }));
    throw new Error(error.detail || 'Failed to unpin job');
  }

  return response.json();
}

/**
 * Clear all unpinned training jobs
 */
export async function clearUnpinnedJobs(): Promise<{ cleared: number; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/status/`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to clear jobs' }));
    throw new Error(error.detail || 'Failed to clear jobs');
  }

  return response.json();
}

/**
 * Train a Transformer model
 */
export async function trainTransformer(
  kmerFile: File,
  phenotypeFile: File,
  options?: {
    model_name?: string;
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    k?: number;
    rosetta_file?: File;
    use_rosetta_preprocessor?: boolean;
    max_genomes?: number;
    cycle_index?: number;
  }
): Promise<TrainingJobResponse> {
  const formData = new FormData();
  formData.append('kmer_file', kmerFile);
  formData.append('phenotype_file', phenotypeFile);
  
  if (options?.model_name) formData.append('model_name', options.model_name);
  if (options?.epochs) formData.append('epochs', options.epochs.toString());
  if (options?.batch_size) formData.append('batch_size', options.batch_size.toString());
  if (options?.learning_rate) formData.append('learning_rate', options.learning_rate.toString());
  if (options?.k) formData.append('k', options.k.toString());
  if (options?.rosetta_file) formData.append('rosetta_file', options.rosetta_file);
  if (options?.use_rosetta_preprocessor !== undefined) {
    formData.append('use_rosetta_preprocessor', String(options.use_rosetta_preprocessor));
  }
  if (options?.max_genomes !== undefined) {
    formData.append('max_genomes', options.max_genomes.toString());
  }
  if (options?.cycle_index !== undefined) {
    formData.append('cycle_index', options.cycle_index.toString());
  }
  
  const response = await fetch(`${API_BASE_URL}/api/train/transformer`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Training request failed' }));
    throw new Error(error.detail || 'Training request failed');
  }
  
  return response.json();
}

/**
 * Train both XGBoost and Transformer models in parallel
 */
export async function trainParallel(
  kmerFile: File,
  phenotypeFile: File,
  options?: {
    model_name?: string;
    xgb_max_depth?: number;
    xgb_learning_rate?: number;
    xgb_n_estimators?: number;
    transformer_epochs?: number;
    transformer_batch_size?: number;
    transformer_learning_rate?: number;
    k?: number;
    rosetta_file?: File;
    use_rosetta_preprocessor?: boolean;
    max_genomes?: number;
    cycle_index?: number;
  }
): Promise<{
  parent_job_id: string;
  xgboost_job_id: string;
  transformer_job_id: string;
  status: string;
  message: string;
  models: { xgboost: string; transformer: string };
}> {
  const formData = new FormData();
  formData.append('kmer_file', kmerFile);
  formData.append('phenotype_file', phenotypeFile);
  
  if (options?.model_name) formData.append('model_name', options.model_name);
  if (options?.xgb_max_depth) formData.append('xgb_max_depth', options.xgb_max_depth.toString());
  if (options?.xgb_learning_rate) formData.append('xgb_learning_rate', options.xgb_learning_rate.toString());
  if (options?.xgb_n_estimators) formData.append('xgb_n_estimators', options.xgb_n_estimators.toString());
  if (options?.transformer_epochs) formData.append('transformer_epochs', options.transformer_epochs.toString());
  if (options?.transformer_batch_size) formData.append('transformer_batch_size', options.transformer_batch_size.toString());
  if (options?.transformer_learning_rate) formData.append('transformer_learning_rate', options.transformer_learning_rate.toString());
  if (options?.k) formData.append('k', options.k.toString());
  if (options?.rosetta_file) formData.append('rosetta_file', options.rosetta_file);
  if (options?.use_rosetta_preprocessor !== undefined) {
    formData.append('use_rosetta_preprocessor', String(options.use_rosetta_preprocessor));
  }
  if (options?.max_genomes !== undefined) {
    formData.append('max_genomes', options.max_genomes.toString());
  }
  if (options?.cycle_index !== undefined) {
    formData.append('cycle_index', options.cycle_index.toString());
  }
  
  const response = await fetch(`${API_BASE_URL}/api/train/parallel`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Parallel training request failed' }));
    throw new Error(error.detail || 'Parallel training request failed');
  }
  
  return response.json();
}

/**
 * Get training job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch job status' }));
    throw new Error(error.detail || 'Failed to fetch job status');
  }
  
  return response.json();
}

/**
 * List all training jobs
 */
export async function listJobs(): Promise<{ total: number; jobs: Array<Partial<JobStatus>> }> {
  const response = await fetch(`${API_BASE_URL}/api/status/`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch jobs');
  }
  
  return response.json();
}

/**
 * Cancel a training job
 */
export async function cancelJob(jobId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to cancel job' }));
    throw new Error(error.detail || 'Failed to cancel job');
  }
  
  return response.json();
}

/**
 * Predict antibiotic resistance from genome
 */
export async function predictResistance(
  genomeFile: File,
  modelMode: 'auto' | 'xgboost' | 'transformer' | 'both' = 'auto',
  options?: { enableBlast?: boolean },
): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append('genome_file', genomeFile);
  formData.append('model_mode', modelMode);
  if (options?.enableBlast !== undefined) {
    formData.append('enable_blast', String(options.enableBlast));
  }
  
  const response = await fetch(`${API_BASE_URL}/api/predict/`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Prediction failed' }));
    throw new Error(error.detail || 'Prediction failed');
  }
  
  return response.json();
}

/**
 * List available trained models
 */
export async function listModels(): Promise<{ models: any[] }> {
  const response = await fetch(`${API_BASE_URL}/api/predict/models`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch models');
  }
  
  return response.json();
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  
  if (!response.ok) {
    throw new Error('API health check failed');
  }
  
  return response.json();
}

