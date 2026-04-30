"""
DNABERT data preprocessing for gene-by-gene analysis.
Handles k=6 k-mer processing and gene sequence tokenization.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
import logging
from io import StringIO
from Bio import SeqIO
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class DNABERTProcessor:
    """
    Processes genomic data for DNABERT Transformer training.
    Uses gene-by-gene approach with k=6 k-mers.
    """
    
    def __init__(self, k: int = 6, max_length: int = 512):
        """
        Initialize DNABERT processor.
        
        Args:
            k: K-mer size
            max_length: Maximum sequence length for DNABERT (512 tokens)
        """
        if k not in (6, 10):
            logger.warning(
                f"DNABERT models are typically pre-trained on k=6 or k=10. "
                f"Using k={k} may not work well."
            )
        
        self.k = k
        self.max_length = max_length
        self.genome_to_genes: Dict[str, List[str]] = {}
    
    def parse_gene_sequences_from_kmer(
        self,
        kmer_content: bytes
    ) -> Dict[str, List[str]]:
        """
        Extract gene sequences from k-mer data.
        Since k-mer data doesn't contain full genes, we'll reconstruct
        approximate gene sequences from k-mer patterns.
        
        Args:
            kmer_content: Raw k-mer file content
        
        Returns:
            Dictionary mapping genome_id to list of gene sequences
        """
        try:
            text_content = kmer_content.decode('utf-8')
            
            # Parse k-mer data
            genome_kmers = defaultdict(list)
            
            for line in text_content.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    # The first column is often a numeric Taxon ID rather than an Assembly Accession
                    genome_id = str(parts[0]).strip()
                    kmer = parts[3]
                    
                    # Only process if k-mer size matches
                    if len(kmer) == self.k:
                        genome_kmers[genome_id].append(kmer)
            
            # Reconstruct gene-like sequences from k-mers
            # Group k-mers into chunks representing "genes"
            genome_to_genes = {}
            
            for genome_id, kmers in genome_kmers.items():
                # Sort k-mers to get some consistency
                kmers_sorted = sorted(set(kmers))
                
                # Create pseudo-genes by grouping k-mers
                # Average bacterial gene is ~1000bp, so ~167 6-mers per gene
                genes_per_genome = []
                chunk_size = 100  # Number of k-mers per "gene"
                
                for i in range(0, len(kmers_sorted), chunk_size):
                    chunk = kmers_sorted[i:i+chunk_size]
                    
                    # Concatenate k-mers with overlap to create gene sequence
                    if len(chunk) > 0:
                        gene_seq = self._reconstruct_sequence_from_kmers(chunk)
                        
                        # Accept sequences of any reasonable length ≥ one k-mer
                        if len(gene_seq) >= self.k:
                            genes_per_genome.append(gene_seq)
            
                if genes_per_genome:
                    genome_to_genes[genome_id] = genes_per_genome[:30]  # Max 30 genes per genome
                elif kmers_sorted:
                    # Fallback: concatenate all available k-mers into one pseudo-sequence
                    # (handles genomes with very few distinct k-mers that produce tiny chunks)
                    fallback_seq = ''.join(kmers_sorted)[:3000]
                    if len(fallback_seq) >= self.k:
                        genome_to_genes[genome_id] = [fallback_seq]
            
            logger.info(f"Extracted genes from {len(genome_to_genes)} genomes")
            logger.info(f"Average genes per genome: {np.mean([len(g) for g in genome_to_genes.values()]):.1f}")
            
            self.genome_to_genes = genome_to_genes
            return genome_to_genes
            
        except Exception as e:
            logger.error(f"Error parsing gene sequences: {e}", exc_info=True)
            raise
    
    def _reconstruct_sequence_from_kmers(self, kmers: List[str]) -> str:
        """
        Reconstruct a sequence from overlapping k-mers.
        
        Args:
            kmers: List of k-mer sequences
        
        Returns:
            Reconstructed DNA sequence
        """
        if not kmers:
            return ""
        
        # Start with first k-mer
        sequence = kmers[0]
        
        # Try to overlap subsequent k-mers
        for kmer in kmers[1:]:
            # Check if this k-mer overlaps with end of sequence
            overlap_found = False
            
            for overlap_len in range(self.k-1, 0, -1):
                if sequence[-overlap_len:] == kmer[:overlap_len]:
                    sequence += kmer[overlap_len:]
                    overlap_found = True
                    break
            
            # If no overlap, just add with small gap
            if not overlap_found:
                sequence += kmer
            
            # Stop if sequence gets too long
            if len(sequence) > 3000:
                break
        
        return sequence
    
    def create_gene_dataset(
        self,
        genome_to_genes: Dict[str, List[str]],
        phenotype_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create gene-level dataset for DNABERT training.
        Each row is a gene with the genome's resistance label.
        
        Args:
            genome_to_genes: Dictionary mapping genome_id to gene sequences
            phenotype_df: DataFrame with phenotype data
        
        Returns:
            DataFrame with columns: genome_id, gene_sequence, antibiotic, resistance_label
        """
        start_time = time.time()
        total_genomes = len(genome_to_genes)
        logger.info(f"Creating gene dataset from {total_genomes} genomes...")

        # Ensure phenotype_df has required columns
        if 'genome_id' not in phenotype_df.columns:
            # Try to infer genome_id column
            genome_cols = ['Genome Name', 'Genome', 'genome_id']
            genome_col = next((c for c in genome_cols if c in phenotype_df.columns), phenotype_df.columns[0])
            phenotype_df = phenotype_df.rename(columns={genome_col: 'genome_id'})
        
        if 'antibiotic' not in phenotype_df.columns:
            antibiotic_cols = ['Antibiotic', 'antibiotic']
            antibiotic_col = next((c for c in antibiotic_cols if c in phenotype_df.columns), None)
            if antibiotic_col:
                phenotype_df = phenotype_df.rename(columns={antibiotic_col: 'antibiotic'})

        logger.info("Indexing phenotype data by genome_id for fast lookup...")
        
        # Reset index in case 'genome_id' was inadvertently set as the index
        if 'genome_id' not in phenotype_df.columns and phenotype_df.index.name == 'genome_id':
            phenotype_df = phenotype_df.reset_index()
            
        # Strip trailing decimals from Genome IDs (e.g. "903915.3" -> "903915") to match k-mer keys
        phenotype_df['genome_id'] = phenotype_df['genome_id'].astype(str).apply(lambda x: x.split('.')[0] if '.' in x else x)
        
        pheno_by_genome = {gid: group for gid, group in phenotype_df.groupby('genome_id')}
        logger.info(f"Indexed phenotypes for {len(pheno_by_genome)} base genomes")
        
        # Create gene-level dataset
        gene_records = []
        processed_with_pheno = 0
        
        for idx, (genome_id, genes) in enumerate(genome_to_genes.items(), start=1):
            # Get phenotypes for this genome
            genome_phenotypes = pheno_by_genome.get(genome_id)
            
            if idx <= 5:
                logger.debug(f"Checking genome_id '{genome_id}'. Has {len(genes)} genes. In pheno_by_genome? {genome_id in pheno_by_genome}")

            processed_with_pheno += 1 if genome_phenotypes is not None else 0
            
            # For each gene, create entries for each antibiotic
            for gene_seq in genes:
                added_any = False
                if genome_phenotypes is not None and not genome_phenotypes.empty:
                    for _, pheno_row in genome_phenotypes.iterrows():
                        antibiotic = pheno_row.get('antibiotic', '')
                        phenotype = pheno_row.get('phenotype', pheno_row.get('Resistant Phenotype', ''))
                        
                        # Encode phenotype
                        if phenotype in ['S', 'Susceptible']:
                            label = 0
                        elif phenotype in ['I', 'Intermediate']:
                            label = 1
                        elif phenotype in ['R', 'Resistant']:
                            label = 2
                        else:
                            continue
                        
                        gene_records.append({
                            'genome_id': genome_id,
                            'gene_sequence': gene_seq,
                            'antibiotic': antibiotic,
                            'label': label
                        })
                        added_any = True

                if not added_any:
                    gene_records.append({
                        'genome_id': genome_id,
                        'gene_sequence': gene_seq,
                        'antibiotic': 'unknown',
                        'label': -1
                    })

            if idx % 10 == 0 or idx == total_genomes:
                elapsed = time.time() - start_time
                avg_per_genome = elapsed / idx if idx > 0 else 0.0
                remaining = total_genomes - idx
                eta = remaining * avg_per_genome
                logger.info(
                    f"[create_gene_dataset] Processed {idx}/{total_genomes} genomes "
                    f"({processed_with_pheno} with phenotypes); "
                    f"elapsed={elapsed/60:.1f} min, ETA={eta/60:.1f} min"
                )
        
        if len(gene_records) == 0:
            gene_df = pd.DataFrame(columns=['genome_id', 'gene_sequence', 'antibiotic', 'label'])
        else:
            gene_df = pd.DataFrame(gene_records)
            
        total_elapsed = time.time() - start_time
        
        logger.info(f"Created gene dataset with {len(gene_df)} entries in {total_elapsed/60:.1f} min")
        logger.info(f"Unique genomes: {gene_df['genome_id'].nunique()}")
        logger.info(f"Unique antibiotics: {gene_df['antibiotic'].nunique()}")
        logger.info(f"Label distribution: S={np.sum(gene_df['label']==0)}, "
                   f"I={np.sum(gene_df['label']==1)}, R={np.sum(gene_df['label']==2)}")
        
        return gene_df
    
    def tokenize_genes_for_dnabert(
        self,
        gene_sequences: List[str],
        tokenizer
    ) -> Dict:
        """
        Tokenize gene sequences using DNABERT tokenizer.
        
        Args:
            gene_sequences: List of gene DNA sequences
            tokenizer: DNABERT tokenizer from transformers
        
        Returns:
            Dictionary with tokenized inputs (input_ids, attention_mask)
        """
        # Convert sequences to k-mer format that DNABERT expects
        kmer_sequences = []
        
        for seq in gene_sequences:
            # Convert to uppercase
            seq = seq.upper()
            
            # Create k-mer representation with spaces (e.g., "ATGCGA" -> "ATGCGA" for k=6)
            # For k=6, we split into overlapping 6-mers
            kmers = []
            for i in range(len(seq) - self.k + 1):
                kmer = seq[i:i+self.k]
                # Only include if all valid nucleotides
                if all(base in 'ACGT' for base in kmer):
                    kmers.append(kmer)
            
            # Join k-mers with spaces (DNABERT format)
            kmer_seq = ' '.join(kmers)
            kmer_sequences.append(kmer_seq)
        
        # Tokenize with DNABERT tokenizer
        tokenized = tokenizer(
            kmer_sequences,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return tokenized
    
    def extract_genes_from_fasta(self, fasta_content: str) -> List[str]:
        """
        Extract gene sequences from FASTA file.
        For prediction on new genomes.
        
        Args:
            fasta_content: FASTA format string
        
        Returns:
            List of gene sequences
        """
        genes = []
        
        # Parse FASTA
        lines = fasta_content.strip().split('\n')
        current_seq = []
        
        for line in lines:
            if line.startswith('>'):
                # New sequence header
                if current_seq:
                    seq = ''.join(current_seq)
                    genes.append(seq)
                    current_seq = []
            else:
                current_seq.append(line.strip().upper())
        
        # Add last sequence
        if current_seq:
            seq = ''.join(current_seq)
            genes.append(seq)
        
        # If only one sequence (whole genome), split into gene-sized chunks
        if len(genes) == 1 and len(genes[0]) > 5000:
            genome = genes[0]
            genes = []
            
            # Split into ~1000bp chunks (average gene size)
            chunk_size = 1000
            for i in range(0, len(genome), chunk_size // 2):  # Overlapping
                chunk = genome[i:i+chunk_size]
                if len(chunk) >= 300:  # Minimum gene size
                    genes.append(chunk)
        
        logger.info(f"Extracted {len(genes)} genes from FASTA")
        
        return genes[:50]  # Limit to 50 genes for memory

