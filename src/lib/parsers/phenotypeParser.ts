/**
 * Parser for phenotype data in the format:
 * Genome Name, Antibiotic, Resistant Phenotype, etc.
 */

export interface PhenotypeEntry {
  genomeName: string;
  antibiotic: string;
  resistantPhenotype: 'Resistant' | 'Susceptible' | 'Intermediate' | '';
  measurementSign: string;
  measurementValue: number | null;
  measurementUnits: string;
  labTypingMethod: string;
  computationalMethod: string;
  evidence: string;
  pubmed: string;
}

export interface PhenotypeData {
  [genomeId: string]: {
    [antibiotic: string]: PhenotypeEntry;
  };
}

/**
 * Parse phenotype data from a CSV string
 * @param csvData Raw phenotype data CSV string
 * @returns Parsed phenotype data
 */
export function parsePhenotypeData(csvData: string): PhenotypeData {
  const lines = csvData.trim().split('\n');
  const phenotypeData: PhenotypeData = {};
  
  // Skip header line
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    // Split by tabs or commas, depending on the format
    const delimiter = line.includes('\t') ? '\t' : ',';
    const fields = line.split(delimiter);
    
    if (fields.length < 3) continue;
    
    const genomeName = fields[0].trim();
    const antibiotic = fields[1].trim().toLowerCase();
    const resistantPhenotype = fields[2].trim() as 'Resistant' | 'Susceptible' | 'Intermediate' | '';
    
    const entry: PhenotypeEntry = {
      genomeName,
      antibiotic,
      resistantPhenotype,
      measurementSign: fields[3]?.trim() || '',
      measurementValue: fields[4]?.trim() ? parseFloat(fields[4]) : null,
      measurementUnits: fields[5]?.trim() || '',
      labTypingMethod: fields[6]?.trim() || '',
      computationalMethod: fields[7]?.trim() || '',
      evidence: fields[8]?.trim() || '',
      pubmed: fields[9]?.trim() || ''
    };
    
    if (!phenotypeData[genomeName]) {
      phenotypeData[genomeName] = {};
    }
    
    phenotypeData[genomeName][antibiotic] = entry;
  }
  
  return phenotypeData;
}

/**
 * Convert phenotype data to labels for machine learning
 * @param phenotypeData Parsed phenotype data
 * @param genomeIds List of genome IDs
 * @param antibiotic Target antibiotic
 * @returns Array of labels (1 for resistant, 0 for susceptible/intermediate)
 */
export function phenotypeDataToLabels(
  phenotypeData: PhenotypeData, 
  genomeIds: string[], 
  antibiotic: string
): number[] {
  return genomeIds.map(genomeId => {
    const antibioticData = phenotypeData[genomeId]?.[antibiotic.toLowerCase()];
    if (!antibioticData) return -1; // Unknown
    
    // Convert phenotype to binary label
    if (antibioticData.resistantPhenotype === 'Resistant') {
      return 1; // Resistant
    } else if (antibioticData.resistantPhenotype === 'Susceptible' || 
               antibioticData.resistantPhenotype === 'Intermediate') {
      return 0; // Susceptible or Intermediate
    }
    
    return -1; // Unknown
  });
}

/**
 * Convert phenotype data to multi-class labels
 * @param phenotypeData Parsed phenotype data
 * @param genomeIds List of genome IDs
 * @param antibiotic Target antibiotic
 * @returns Array of labels ('R', 'I', 'S', or '' for unknown)
 */
export function phenotypeDataToMultiClassLabels(
  phenotypeData: PhenotypeData, 
  genomeIds: string[], 
  antibiotic: string
): string[] {
  return genomeIds.map(genomeId => {
    const antibioticData = phenotypeData[genomeId]?.[antibiotic.toLowerCase()];
    if (!antibioticData) return ''; // Unknown
    
    // Convert phenotype to label
    if (antibioticData.resistantPhenotype === 'Resistant') {
      return 'R';
    } else if (antibioticData.resistantPhenotype === 'Intermediate') {
      return 'I';
    } else if (antibioticData.resistantPhenotype === 'Susceptible') {
      return 'S';
    }
    
    return ''; // Unknown
  });
}