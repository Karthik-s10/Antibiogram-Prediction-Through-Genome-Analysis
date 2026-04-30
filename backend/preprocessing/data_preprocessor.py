"""
Data Preprocessor for Genomic AMR Analysis
Handles ID mapping between PATRIC Genome IDs and GenBank Accessions,
and aligns phenotype and k-mer data for model training.
"""

import pandas as pd
import numpy as np
from scipy import sparse
from pathlib import Path
from typing import Tuple, Dict, Optional, List, Set
import logging
from datetime import datetime

from preprocessing.phenotype_parser import PhenotypeParser

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocesses genomic data by mapping IDs and aligning features with labels.
    
    This class handles the critical step of resolving ID mismatches between:
    - Phenotype data (uses PATRIC Genome IDs like "562.xxx")
    - K-mer data (uses GenBank Accession IDs like "GCA_xxx")
    
    It uses a "Rosetta Stone" mapping file to bridge these ID formats.
    """
    
    def __init__(
        self,
        rosetta_file: str = "BVBRC_genome.txt",
        cache_dir: str = "./data_cache"
    ):
        """
        Initialize the data preprocessor.
        
        Args:
            rosetta_file: Path to the BVBRC_genome.txt mapping file
            cache_dir: Directory to store cached aligned data
        """
        self.rosetta_file = Path(rosetta_file)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.id_mapping: Optional[Dict[str, str]] = None
        # Assembly-level metadata (e.g. species/strain) keyed by Assembly Accession
        self.assembly_metadata: Dict[str, Dict[str, str]] = {}
        self._cache_file = self.cache_dir / "aligned_data_cache.pkl"
        
    def load_id_mapping(self) -> Dict[str, str]:
        """
        Load the ID mapping from BVBRC_genome.txt.
        
        Creates a dictionary mapping PATRIC Genome IDs to Assembly Accessions (GCA_xxx format).
        Uses chunked reading to handle large files efficiently.
        
        Returns:
            Dictionary mapping {PATRIC_ID: Assembly_Accession}
        """
        if self.id_mapping is not None:
            logger.info("Using cached ID mapping")
            return self.id_mapping
        
        logger.info(f"Loading ID mapping from {self.rosetta_file}")
        
        if not self.rosetta_file.exists():
            raise FileNotFoundError(
                f"Rosetta Stone file not found: {self.rosetta_file}\n"
                "This file is required to map PATRIC IDs to Assembly Accessions."
            )
        
        id_mapping = {}
        chunk_size = 100000
        
        try:
            # Read in chunks to handle large files
            # Use 'Assembly Accession' column which has GCA_xxx format matching k-mer file
            for chunk in pd.read_csv(
                self.rosetta_file,
                sep='\t',
                chunksize=chunk_size,
                usecols=['Genome ID', 'Assembly Accession'],
                dtype=str,
                low_memory=False
            ):
                # Remove quotes and whitespace
                chunk['Genome ID'] = chunk['Genome ID'].str.strip().str.replace('"', '')
                chunk['Assembly Accession'] = chunk['Assembly Accession'].str.strip().str.replace('"', '')
                
                # Filter out rows with missing values
                chunk = chunk.dropna(subset=['Genome ID', 'Assembly Accession'])
                
                # Update mapping dictionary
                for _, row in chunk.iterrows():
                    genome_id = row['Genome ID']
                    assembly_acc = row['Assembly Accession']
                    
                    # Handle multiple accessions (comma-separated)
                    if ',' in assembly_acc:
                        assembly_acc = assembly_acc.split(',')[0].strip()
                    
                    id_mapping[genome_id] = assembly_acc
            
            logger.info(f"Loaded {len(id_mapping)} ID mappings")
            self.id_mapping = id_mapping
            return id_mapping
            
        except Exception as e:
            logger.error(f"Error loading ID mapping: {e}")
            raise
    
    def load_and_map_phenotypes(
        self,
        phenotype_file: str,
        id_mapping: Dict[str, str],
        use_taxon_id: bool = False
    ) -> pd.DataFrame:
        """
        Load phenotype data and map PATRIC IDs to Assembly Accessions (GCA_xxx format).
        
        Args:
            phenotype_file: Path to BVBRC_genome_amr.txt
            id_mapping: Dictionary mapping PATRIC IDs to Assembly Accessions
            
        Returns:
            DataFrame with Assembly Accession column added
        """
        logger.info(f"Loading phenotype data from {phenotype_file}")
        
        try:
            # Read phenotype file
            pheno_df = pd.read_csv(
                phenotype_file,
                sep='\t',
                dtype=str,
                low_memory=False
            )
            
            # Clean column names
            pheno_df.columns = pheno_df.columns.str.strip()
            
            # Remove quotes from Genome ID and Antibiotic columns
            pheno_df['Genome ID'] = pheno_df['Genome ID'].str.strip().str.replace('"', '')
            pheno_df['Antibiotic'] = pheno_df['Antibiotic'].str.strip().str.replace('"', '')

            # Normalize antibiotic names to match PhenotypeParser behavior
            pheno_df['Antibiotic'] = pheno_df['Antibiotic'].str.lower()
            pheno_df['Antibiotic'] = pheno_df['Antibiotic'].map(
                PhenotypeParser.ANTIBIOTIC_NORMALIZATION_MAP
            ).fillna(pheno_df['Antibiotic'])
            
            # Filter for Laboratory Method evidence only
            if 'Evidence' in pheno_df.columns:
                pheno_df = pheno_df[pheno_df['Evidence'] == 'Laboratory Method']
                logger.info(f"Filtered to {len(pheno_df)} laboratory-validated records")
            
            if use_taxon_id:
                pheno_df['Assembly Accession'] = pheno_df['Taxon ID'].astype(str).str.strip()
            else:
                # Map PATRIC IDs to Assembly Accessions (GCA_xxx format to match k-mer file)
                pheno_df['Assembly Accession'] = pheno_df['Genome ID'].map(id_mapping)
            
            # Remove rows without mapping
            before_count = len(pheno_df)
            pheno_df = pheno_df.dropna(subset=['Assembly Accession'])
            after_count = len(pheno_df)
            
            logger.info(
                f"Mapped {after_count} phenotype records "
                f"({before_count - after_count} unmapped records dropped)"
            )
            
            # Build assembly-level metadata (organism / genome name and strain) for later use
            try:
                cols = pheno_df.columns
                has_name_cols = any(c in cols for c in ["Genome Name", "Organism Name", "Organism"])
                has_strain_col = "Strain" in cols

                if has_name_cols or has_strain_col:
                    subset_cols = ["Assembly Accession"]
                    for c in ["Genome Name", "Organism Name", "Organism", "Strain"]:
                        if c in cols:
                            subset_cols.append(c)

                    meta_df = pheno_df[subset_cols].dropna(subset=["Assembly Accession"])

                    for _, row in meta_df.iterrows():
                        assembly = str(row["Assembly Accession"]).strip()
                        if not assembly:
                            continue

                        meta = self.assembly_metadata.get(assembly, {})

                        genome_name = None
                        if "Genome Name" in meta_df.columns and pd.notna(row["Genome Name"]):
                            genome_name = str(row["Genome Name"]).strip()

                        organism_name = None
                        if "Organism Name" in meta_df.columns and pd.notna(row["Organism Name"]):
                            organism_name = str(row["Organism Name"]).strip()
                        elif "Organism" in meta_df.columns and pd.notna(row["Organism"]):
                            organism_name = str(row["Organism"]).strip()

                        strain = None
                        if "Strain" in meta_df.columns and pd.notna(row["Strain"]):
                            strain = str(row["Strain"]).strip()

                        if genome_name and "genome_name" not in meta:
                            meta["genome_name"] = genome_name
                        if organism_name and "organism_name" not in meta:
                            meta["organism_name"] = organism_name
                        if strain and "strain" not in meta:
                            meta["strain"] = strain

                        if meta:
                            self.assembly_metadata[assembly] = meta
            except Exception as e:
                logger.warning(f"Failed to build assembly metadata from phenotype data: {e}")
            
            return pheno_df
            
        except Exception as e:
            logger.error(f"Error loading phenotype data: {e}")
            raise
    
    def create_label_matrix(self, pheno_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create label matrix (Y) from phenotype data.
        
        Pivots the data so that:
        - Rows = Assembly Accessions (GCA_xxx format)
        - Columns = Antibiotics
        - Values = Encoded resistance (0=S, 1=I, 2=R)
        
        Args:
            pheno_df: Phenotype DataFrame with Assembly Accession column
            
        Returns:
            Pivoted label matrix
        """
        logger.info("Creating label matrix (Y)")
        
        # Encode resistance phenotypes
        resistance_map = {
            'Susceptible': 0,
            'Intermediate': 1,
            'Resistant': 2
        }
        
        pheno_df['Label'] = pheno_df['Resistant Phenotype'].map(resistance_map)
        
        # Remove rows with unmapped phenotypes
        pheno_df = pheno_df.dropna(subset=['Label'])
        
        # Pivot to create matrix (use Assembly Accession to match k-mer file)
        Y = pheno_df.pivot_table(
            index='Assembly Accession',
            columns='Antibiotic',
            values='Label',
            aggfunc='first'  # Use first value if duplicates exist
        )
        
        logger.info(f"Label matrix shape: {Y.shape} (genomes x antibiotics)")
        logger.info(f"Antibiotics: {list(Y.columns)}")
        
        return Y
    
    def load_kmer_data(self, kmer_file: str, chunk_size: int = 500000) -> pd.DataFrame:
        """
        Load k-mer data from file.
        
        Uses chunked reading to handle large files efficiently.
        
        Args:
            kmer_file: Path to SIGNIFICANT_DNA_KMERS_BACTERIA file
            chunk_size: Number of rows to read per chunk
            
        Returns:
            DataFrame with k-mer data
        """
        logger.info(f"Loading k-mer data from {kmer_file}")
        
        try:
            chunks = []
            
            # Read in chunks
            for i, chunk in enumerate(pd.read_csv(
                kmer_file,
                sep='\t',
                header=None,
                names=['Genome ID', 'Domain', 'k', 'kmer_sequence', 'prob1', 'prob2'],
                chunksize=chunk_size,
                dtype={'Genome ID': str, 'Domain': str, 'k': int, 'kmer_sequence': str, 
                       'prob1': float, 'prob2': float},
                low_memory=False
            )):
                chunks.append(chunk)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Loaded {(i + 1) * chunk_size} k-mer records...")
            
            # Combine all chunks
            kmer_df = pd.concat(chunks, ignore_index=True)
            logger.info(f"Total k-mer records loaded: {len(kmer_df)}")
            
            return kmer_df
            
        except Exception as e:
            logger.error(f"Error loading k-mer data: {e}")
            raise
    
    def create_feature_matrix(
        self,
        kmer_df: pd.DataFrame,
        target_genomes: Optional[Set[str]] = None,
        use_prob2: bool = True
    ) -> pd.DataFrame:
        """
        Create feature matrix (X) from k-mer data using sparse matrix construction.
        
        This method is memory-efficient and can handle millions of k-mers.
        
        Args:
            kmer_df: K-mer DataFrame
            target_genomes: Optional set of genome IDs to filter to (for memory efficiency)
            use_prob2: If True, use prob2 column; otherwise use prob1
            
        Returns:
            Feature matrix as DataFrame (genomes x k-mers)
        """
        logger.info("Creating feature matrix (X) using sparse matrix construction")
        
        value_col = 'prob2' if use_prob2 else 'prob1'
        
        # Filter to target genomes if provided (huge memory savings)
        if target_genomes:
            original_len = len(kmer_df)
            kmer_df = kmer_df[kmer_df['Genome ID'].isin(target_genomes)]
            logger.info(f"Filtered k-mers from {original_len:,} to {len(kmer_df):,} records (genomes in phenotype data)")
        
        if len(kmer_df) == 0:
            raise ValueError("No k-mer data remaining after filtering to target genomes")
        
        # Get unique genomes and k-mers
        logger.info("Building genome and k-mer indices...")
        unique_genomes = kmer_df['Genome ID'].unique()
        unique_kmers = kmer_df['kmer_sequence'].unique()
        
        n_genomes = len(unique_genomes)
        n_kmers = len(unique_kmers)
        
        logger.info(f"Matrix dimensions: {n_genomes:,} genomes x {n_kmers:,} k-mers")
        logger.info(f"Sparse matrix will use ~{(len(kmer_df) * 12) / (1024**2):.1f} MB instead of ~{(n_genomes * n_kmers * 8) / (1024**3):.1f} GB dense")
        
        # Create mappings for sparse matrix construction
        genome_to_idx = {g: i for i, g in enumerate(unique_genomes)}
        kmer_to_idx = {k: i for i, k in enumerate(unique_kmers)}
        
        # Build sparse matrix using COO format (fastest for construction)
        logger.info("Building sparse matrix...")
        row_indices = []
        col_indices = []
        values = []
        
        for i, (genome_id, kmer_seq, value) in enumerate(
            zip(kmer_df['Genome ID'], kmer_df['kmer_sequence'], kmer_df[value_col])
        ):
            row_indices.append(genome_to_idx[genome_id])
            col_indices.append(kmer_to_idx[kmer_seq])
            values.append(value)
            
            if (i + 1) % 5000000 == 0:
                logger.info(f"Processed {i + 1:,} / {len(kmer_df):,} k-mer records...")
        
        # Create sparse matrix
        sparse_matrix = sparse.coo_matrix(
            (values, (row_indices, col_indices)),
            shape=(n_genomes, n_kmers),
            dtype=np.float32
        )
        
        # Convert to CSR for efficient row operations
        sparse_matrix = sparse_matrix.tocsr()
        
        logger.info(f"Sparse matrix created: {sparse_matrix.nnz:,} non-zero entries")
        logger.info(f"Sparsity: {(1 - sparse_matrix.nnz / (n_genomes * n_kmers)) * 100:.2f}%")
        
        # Convert to DataFrame (dense, but now much smaller due to filtering)
        logger.info("Converting to DataFrame...")
        X = pd.DataFrame(
            sparse_matrix.toarray(),
            index=unique_genomes,
            columns=unique_kmers
        )
        
        logger.info(f"Feature matrix shape: {X.shape} (genomes x k-mers)")
        
        return X
    
    def align_data(
        self,
        X: pd.DataFrame,
        Y: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align feature and label matrices.
        
        Uses inner join to keep only genomes present in both datasets.
        
        Args:
            X: Feature matrix (genomes x k-mers)
            Y: Label matrix (genomes x antibiotics)
            
        Returns:
            Tuple of (X_final, Y_final) with aligned indices
        """
        logger.info("Aligning feature and label matrices")
        
        # Align using inner join
        X_final, Y_final = X.align(Y, join='inner', axis=0)
        
        logger.info(f"Alignment complete:")
        logger.info(f"  - Matched genomes: {len(X_final)}")
        logger.info(f"  - Features (k-mers): {X_final.shape[1]}")
        logger.info(f"  - Labels (antibiotics): {Y_final.shape[1]}")
        logger.info(f"  - Total data points: {X_final.shape[0] * X_final.shape[1]}")
        
        if len(X_final) == 0:
            raise ValueError(
                "No matching genomes found between k-mer and phenotype data. "
                "Check that the ID mapping is correct."
            )
        
        return X_final, Y_final
    
    def preprocess_data(
        self,
        phenotype_file: str,
        kmer_file: str,
        use_cache: bool = True,
        save_cache: bool = True,
        use_taxon_id: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Main preprocessing pipeline.
        
        Orchestrates the entire data preprocessing workflow:
        1. Load ID mapping
        2. Load and map phenotype data
        3. Create label matrix
        4. Load k-mer data
        5. Create feature matrix
        6. Align matrices
        
        Args:
            phenotype_file: Path to BVBRC_genome_amr.txt
            kmer_file: Path to SIGNIFICANT_DNA_KMERS_BACTERIA
            use_cache: If True, try to load from cache
            save_cache: If True, save results to cache
            
        Returns:
            Tuple of (X_final, Y_final) aligned DataFrames
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting data preprocessing pipeline")
        logger.info("=" * 80)
        
        # Check cache
        if use_cache and self._cache_file.exists():
            logger.info(f"Loading aligned data from cache: {self._cache_file}")
            try:
                cache_data = pd.read_pickle(self._cache_file)
                X_final = cache_data['X']
                Y_final = cache_data['Y']
                logger.info("Cache loaded successfully")
                logger.info(f"  - Genomes: {len(X_final)}")
                logger.info(f"  - Features: {X_final.shape[1]}")
                logger.info(f"  - Labels: {Y_final.shape[1]}")

                data_summary = {
                    'n_phenotype_records': None,
                    'n_kmer_records': None,
                    'n_phenotype_genomes': int(len(Y_final)),
                    'n_kmer_genomes': int(len(X_final)),
                    'n_aligned_genomes': int(len(X_final)),
                }

                return X_final, Y_final, data_summary
            except Exception as e:
                logger.warning(f"Cache load failed: {e}. Proceeding with full preprocessing.")
        
        # Step 1: Load ID mapping
        id_mapping = self.load_id_mapping()
        
        # Step 2: Load and map phenotype data
        pheno_df = self.load_and_map_phenotypes(phenotype_file, id_mapping, use_taxon_id=use_taxon_id)
        n_phenotype_records = len(pheno_df)
        # Count unique genomes in phenotype after mapping (Assembly Accession index space)
        n_phenotype_genomes = int(pheno_df['Assembly Accession'].nunique())
        
        # Step 3: Create label matrix
        Y = self.create_label_matrix(pheno_df)
        
        # Step 4: Load k-mer data
        kmer_df = self.load_kmer_data(kmer_file)
        n_kmer_records = len(kmer_df)
        total_kmer_genomes = int(kmer_df['Genome ID'].nunique())
        
        # Step 5: Create feature matrix (filter to genomes in Y for memory efficiency)
        target_genomes = set(Y.index)
        logger.info(f"Filtering k-mers to {len(target_genomes)} genomes from phenotype data")
        X = self.create_feature_matrix(kmer_df, target_genomes=target_genomes)
        n_kmer_genomes_after_filter = int(len(X))
        
        # Free memory from kmer_df
        del kmer_df
        
        # Step 6: Align matrices
        X_final, Y_final = self.align_data(X, Y)
        n_aligned_genomes = int(len(X_final))
        
        # Save to cache
        if save_cache:
            logger.info(f"Saving aligned data to cache: {self._cache_file}")
            try:
                cache_data = {'X': X_final, 'Y': Y_final}
                pd.to_pickle(cache_data, self._cache_file)
                logger.info("Cache saved successfully")
            except Exception as e:
                logger.warning(f"Cache save failed: {e}")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info(f"Preprocessing complete in {elapsed:.2f} seconds")
        logger.info("=" * 80)

        data_summary = {
            'n_phenotype_records': int(n_phenotype_records),
            'n_kmer_records': int(n_kmer_records),
            'n_phenotype_genomes': int(n_phenotype_genomes),
            'n_kmer_genomes': int(total_kmer_genomes),
            'n_kmer_genomes_after_filter': int(n_kmer_genomes_after_filter),
            'n_aligned_genomes': int(n_aligned_genomes),
        }
        
        return X_final, Y_final, data_summary
    
    def get_data_summary(self, X: pd.DataFrame, Y: pd.DataFrame) -> Dict:
        """
        Get summary statistics of the aligned data.
        
        Args:
            X: Feature matrix
            Y: Label matrix
            
        Returns:
            Dictionary with summary statistics
        """
        return {
            'n_genomes': len(X),
            'n_features': X.shape[1],
            'n_antibiotics': Y.shape[1],
            'antibiotics': list(Y.columns),
            'feature_sparsity': (X == 0).sum().sum() / (X.shape[0] * X.shape[1]),
            'label_distribution': {
                antibiotic: Y[antibiotic].value_counts().to_dict()
                for antibiotic in Y.columns
            }
        }
