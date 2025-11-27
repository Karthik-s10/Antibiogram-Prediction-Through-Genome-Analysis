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
  predictions: Array<{
    antibiotic: string;
    prediction: 'S' | 'I' | 'R';
    confidence: number;
    markers?: Array<{
      name: string;
      impact: number;
      confidence: number;
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
    }>;
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
export async function predictResistance(genomeFile: File): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append('genome_file', genomeFile);
  
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

