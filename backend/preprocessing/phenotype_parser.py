"""
Phenotype data parser for antibiotic resistance labels.
Converts CSV phenotype data into label matrices for ML training.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from io import StringIO
import logging

logger = logging.getLogger(__name__)


class PhenotypeParser:
    """
    Parses phenotype CSV files and creates label matrices.
    Handles S/I/R encoding and multi-label formatting.
    """
    
    # Resistance encoding
    RESISTANCE_MAP = {
        'Susceptible': 0,
        'S': 0,
        'Intermediate': 1,
        'I': 1,
        'Resistant': 2,
        'R': 2,
        # Additional BV-BRC style values
        'Nonsusceptible': 2,
        'Reduced Susceptibility': 1,
        'Susceptible-dose dependent': 1,
    }
    
    def __init__(self):
        self.antibiotics: List[str] = []
        self.genome_ids: List[str] = []
        
    # Map obvious antibiotic spelling variants to canonical names
    ANTIBIOTIC_NORMALIZATION_MAP: Dict[str, str] = {
        'trimotheprim': 'trimethoprim',
        'tigecyklin': 'tigecycline',
        'tgecycline': 'tigecycline',
        'strofurantoin': 'nitrofurantoin',
        'phosphomycin': 'fosfomycin',
        'cefuroximâ': 'cefuroxime',
        'ceftarolin': 'ceftaroline',
        'cefalexin': 'cephalexin',
        'cefalotin': 'cephalothin',
        'cefpirom': 'cefpirome',
        'amoxicillin_clavulanat': 'amoxicillin/clavulanic acid',
        'sulfamethoxazole/trimethoprim': 'trimethoprim/sulfamethoxazole',
        # Additional variants seen in BV-BRC phenotype exports
        'cefotaxime/clavulanic acidâ': 'cefotaxime/clavulanic acid',
        'tetracyklin': 'tetracycline',
        'aminogycosides': 'aminoglycosides',
        'geamycin': 'gentamicin',
        'trimethoprim_sulfonamide': 'trimethoprim/sulfonamide',
        'sulphadimethoxine': 'sulfadimethoxine',
    }
    
    def parse_phenotype_file(self, content: bytes) -> pd.DataFrame:
        """
        Parse phenotype CSV file.
        
        Expected columns:
        - Genome Name (or similar genome identifier)
        - Antibiotic
        - Resistant Phenotype (S/I/R or Susceptible/Intermediate/Resistant)
        
        Additional optional columns:
        - Measurement Sign, Measurement Value, Measurement Units, Lab typing Method, etc.
        
        Args:
            content: Raw CSV file content in bytes
        
        Returns:
            DataFrame with parsed phenotype data
        """
        try:
            # Decode content
            text_content = content.decode('utf-8')
            
            # Try to detect delimiter by analyzing the first few lines
            first_line = text_content.split('\n')[0] if '\n' in text_content else text_content
            tab_count = first_line.count('\t')
            comma_count = first_line.count(',')
            
            # Determine best delimiter
            if tab_count > comma_count:
                # Likely tab-separated
                logger.info("Detected tab-separated format (TSV)")
                delimiter = '\t'
            elif comma_count > 0:
                # Likely comma-separated
                logger.info("Detected comma-separated format (CSV)")
                delimiter = ','
            else:
                # Try auto-detection
                logger.info("Attempting auto-detection of delimiter")
                delimiter = None
            
            # Read CSV with detected or auto-detected delimiter
            try:
                try:
                    df = pd.read_csv(
                        StringIO(text_content), 
                        sep=delimiter, 
                        skipinitialspace=True, 
                        on_bad_lines='warn',
                        engine='python' if delimiter is None else 'c'
                    )
                except TypeError:
                    # Fallback for older pandas versions
                    df = pd.read_csv(
                        StringIO(text_content), 
                        sep=delimiter, 
                        skipinitialspace=True, 
                        error_bad_lines=False, 
                        warn_bad_lines=True,
                        engine='python' if delimiter is None else 'c'
                    )
            except Exception as e:
                logger.warning(f"Failed to parse with detected delimiter, trying tab-separated...")
                try:
                    # Force tab-separated
                    try:
                        df = pd.read_csv(StringIO(text_content), sep='\t', skipinitialspace=True, on_bad_lines='warn')
                    except TypeError:
                        df = pd.read_csv(StringIO(text_content), sep='\t', skipinitialspace=True, error_bad_lines=False, warn_bad_lines=True)
                except Exception as e2:
                    logger.warning(f"Failed tab-separated, trying comma-separated...")
                    # Force comma-separated
                    try:
                        df = pd.read_csv(StringIO(text_content), sep=',', skipinitialspace=True, on_bad_lines='warn')
                    except TypeError:
                        df = pd.read_csv(StringIO(text_content), sep=',', skipinitialspace=True, error_bad_lines=False, warn_bad_lines=True)
            
            # Check if we got a single column (likely wrong delimiter)
            if len(df.columns) == 1:
                logger.warning("Only one column detected, likely wrong delimiter. Trying tab-separated...")
                try:
                    df = pd.read_csv(StringIO(text_content), sep='\t', skipinitialspace=True, on_bad_lines='warn')
                    logger.info("Successfully parsed as tab-separated")
                except:
                    pass
            
            # Remove any completely empty rows
            df = df.dropna(how='all')
            
            # Remove any rows where all values are empty strings
            df = df[~(df.astype(str).eq('').all(axis=1))]
            
            logger.info(f"Parsed phenotype file with {len(df)} rows")
            logger.info(f"Columns ({len(df.columns)}): {df.columns.tolist()}")
            
            # Standardize column names - remove extra whitespace and tabs
            df.columns = df.columns.str.strip().str.replace('\t', ' ')
            
            # Find genome identifier column - expanded list with more variations.
            # Prefer Taxon ID when available so we can align directly with
            # taxon-based k-mer files.
            genome_cols = [
                'Taxon ID',
                'Genome ID',
                'Genome Name',
                'Genome',
                'genome_id',
                'genome',
                'Genome',
                'GenomeName',
                'genome_name',
            ]
            genome_col = None
            for col in genome_cols:
                if col in df.columns:
                    genome_col = col
                    break
            
            if not genome_col:
                raise ValueError(f"Could not find genome identifier column. Available: {df.columns.tolist()}")
            
            # Find antibiotic column
            antibiotic_cols = ['Antibiotic', 'antibiotic', 'Drug', 'drug']
            antibiotic_col = None
            for col in antibiotic_cols:
                if col in df.columns:
                    antibiotic_col = col
                    break
            
            if not antibiotic_col:
                raise ValueError(f"Could not find antibiotic column. Available: {df.columns.tolist()}")
            
            # Find resistance phenotype column
            phenotype_cols = ['Resistant Phenotype', 'Resistance', 'Phenotype', 'resistance', 'phenotype']
            phenotype_col = None
            for col in phenotype_cols:
                if col in df.columns:
                    phenotype_col = col
                    break
            
            if not phenotype_col:
                raise ValueError(f"Could not find phenotype column. Available: {df.columns.tolist()}")
            
            # Standardize column names
            df = df.rename(columns={
                genome_col: 'genome_id',
                antibiotic_col: 'antibiotic',
                phenotype_col: 'phenotype'
            })
            
            # Keep only necessary columns
            df = df[['genome_id', 'antibiotic', 'phenotype']]
            
            # Clean data
            df['genome_id'] = df['genome_id'].astype(str).str.strip()
            df['antibiotic'] = df['antibiotic'].astype(str).str.strip().str.lower()
            df['antibiotic'] = df['antibiotic'].map(self.ANTIBIOTIC_NORMALIZATION_MAP).fillna(df['antibiotic'])
            df['phenotype'] = df['phenotype'].astype(str).str.strip()
            
            # Remove any rows with missing values
            df = df.dropna()
            
            logger.info(f"Cleaned phenotype data: {len(df)} entries")
            logger.info(f"Unique genomes: {df['genome_id'].nunique()}")
            logger.info(f"Unique antibiotics: {df['antibiotic'].nunique()}")
            logger.info(f"Antibiotics: {sorted(df['antibiotic'].unique())}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing phenotype file: {e}", exc_info=True)
            raise ValueError(f"Failed to parse phenotype file: {str(e)}")
    
    def encode_phenotypes(self, phenotype_df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode resistance phenotypes as numeric values.
        
        Args:
            phenotype_df: DataFrame with phenotype data
        
        Returns:
            DataFrame with encoded phenotypes
        """
        df = phenotype_df.copy()
        
        # Map phenotypes to numeric values
        df['encoded'] = df['phenotype'].map(self.RESISTANCE_MAP)
        
        # Check for unmapped values
        unmapped = df[df['encoded'].isna()]['phenotype'].unique()
        if len(unmapped) > 0:
            logger.warning(f"Unmapped phenotype values: {unmapped}")
            # Try to infer based on first letter
            for val in unmapped:
                if val.upper().startswith('S'):
                    df.loc[df['phenotype'] == val, 'encoded'] = 0
                elif val.upper().startswith('I'):
                    df.loc[df['phenotype'] == val, 'encoded'] = 1
                elif val.upper().startswith('R'):
                    df.loc[df['phenotype'] == val, 'encoded'] = 2
        
        # Drop rows with still unmapped values
        df = df.dropna(subset=['encoded'])
        df['encoded'] = df['encoded'].astype(int)
        
        return df
    
    def build_label_matrix(
        self,
        phenotype_df: pd.DataFrame,
        genome_ids: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Build label matrix aligned with feature matrix genome order.
        
        Args:
            phenotype_df: DataFrame with encoded phenotype data
            genome_ids: List of genome IDs from feature matrix (for alignment)
        
        Returns:
            Tuple of (label_matrix, antibiotic_names)
            - label_matrix: numpy array (n_genomes × n_antibiotics)
            - antibiotic_names: list of antibiotic names
        """
        # Encode phenotypes
        df = self.encode_phenotypes(phenotype_df)
        
        # Get unique antibiotics
        antibiotics = sorted(df['antibiotic'].unique())
        
        # Create pivot table: rows=genomes, columns=antibiotics, values=encoded resistance
        pivot = df.pivot_table(
            index='genome_id',
            columns='antibiotic',
            values='encoded',
            aggfunc='first'  # Use first value if duplicates exist
        )
        
        # Align with provided genome_ids
        n_genomes = len(genome_ids)
        n_antibiotics = len(antibiotics)
        
        label_matrix = np.full((n_genomes, n_antibiotics), -1, dtype=np.int8)  # -1 for missing
        
        for i, genome in enumerate(genome_ids):
            if genome in pivot.index:
                for j, antibiotic in enumerate(antibiotics):
                    if antibiotic in pivot.columns:
                        val = pivot.loc[genome, antibiotic]
                        if not pd.isna(val):
                            label_matrix[i, j] = int(val)
        
        # Store for later use
        self.genome_ids = genome_ids
        self.antibiotics = antibiotics
        
        # Count missing labels
        missing_count = (label_matrix == -1).sum()
        total_labels = label_matrix.size
        
        logger.info(f"Built label matrix: {label_matrix.shape}")
        logger.info(f"Missing labels: {missing_count}/{total_labels} ({missing_count/total_labels*100:.2f}%)")
        logger.info(f"Label distribution: S={np.sum(label_matrix==0)}, I={np.sum(label_matrix==1)}, R={np.sum(label_matrix==2)}")
        
        return label_matrix, antibiotics
    
    def align_data(
        self,
        feature_genome_ids: List[str],
        phenotype_df: pd.DataFrame
    ) -> Tuple[List[str], np.ndarray, List[str]]:
        """
        Align feature matrix genomes with phenotype data.
        Returns only genomes that have both features and labels.
        
        Args:
            feature_genome_ids: List of genome IDs from k-mer data
            phenotype_df: DataFrame with phenotype data
        
        Returns:
            Tuple of (aligned_genome_ids, label_matrix, antibiotic_names)
        """
        # Get genomes that have phenotype data
        phenotype_genomes = set(phenotype_df['genome_id'].unique())
        
        # Find intersection
        aligned_genomes = [g for g in feature_genome_ids if g in phenotype_genomes]
        
        logger.info(f"Feature genomes: {len(feature_genome_ids)}")
        logger.info(f"Phenotype genomes: {len(phenotype_genomes)}")
        logger.info(f"Aligned genomes: {len(aligned_genomes)}")
        
        if len(aligned_genomes) == 0:
            raise ValueError("No genomes found in both k-mer and phenotype data!")
        
        # Build label matrix for aligned genomes
        label_matrix, antibiotics = self.build_label_matrix(phenotype_df, aligned_genomes)
        
        return aligned_genomes, label_matrix, antibiotics

