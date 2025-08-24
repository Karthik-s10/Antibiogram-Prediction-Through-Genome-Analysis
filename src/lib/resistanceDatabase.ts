// Comprehensive resistance gene database with known markers
export interface ResistanceGene {
  id: string;
  name: string;
  description: string;
  antibioticClass: string[];
  mechanism: string;
  sequence?: string; // Simplified - in real implementation would be full sequences
  patterns: string[]; // Key sequence patterns to look for
}

export const RESISTANCE_GENES: ResistanceGene[] = [
  // Beta-lactam resistance
  {
    id: "blaTEM-1",
    name: "blaTEM-1",
    description: "Beta-lactamase TEM-1",
    antibioticClass: ["ampicillin", "amoxicillin", "penicillin"],
    mechanism: "Beta-lactamase production",
    patterns: [
      "ATGAGTATTCAACATTTCCG",
      "TCCGTGTCGCCCTTATTC",
      "GAGTATTCAACATTTTCG",
    ],
  },
  {
    id: "blaCTX-M",
    name: "blaCTX-M",
    description: "Extended-spectrum beta-lactamase CTX-M",
    antibioticClass: ["ceftriaxone", "cefotaxime", "ampicillin"],
    mechanism: "Extended-spectrum beta-lactamase",
    patterns: [
      "ATGTGCAGYACCAGTAARGT",
      "CGCTTTGCGATGTGCAG",
      "TGCAGYACCAGTAARGT",
    ],
  },
  {
    id: "ampC",
    name: "ampC",
    description: "Beta-lactamase AmpC",
    antibioticClass: ["ampicillin", "cephalexin"],
    mechanism: "Chromosomal beta-lactamase",
    patterns: ["ATGAAAAAACTGTTGCTG", "CTGTTGCTGGATAGTGAC", "AAAAAACTGTTGCTGGA"],
  },

  // Aminoglycoside resistance
  {
    id: "aac3-IIa",
    name: "aac(3)-IIa",
    description: "Aminoglycoside acetyltransferase",
    antibioticClass: ["gentamicin", "tobramycin"],
    mechanism: "Enzymatic modification",
    patterns: ["ATGGATGAGCACGAATTT", "GGATGAGCACGAATTTGC", "TGAGCACGAATTTGCCG"],
  },
  {
    id: "aph3-Ia",
    name: "aph(3)-Ia",
    description: "Aminoglycoside phosphotransferase",
    antibioticClass: ["gentamicin", "kanamycin"],
    mechanism: "Enzymatic modification",
    patterns: [
      "ATGAGCCATATTCAACGGG",
      "GCCATATTCAACGGGAAA",
      "CATATTCAACGGGAAACG",
    ],
  },

  // Quinolone resistance
  {
    id: "qnrS1",
    name: "qnrS1",
    description: "Quinolone resistance protein",
    antibioticClass: ["ciprofloxacin", "levofloxacin"],
    mechanism: "Target protection",
    patterns: [
      "ATGAAATCGACGCCGACTTC",
      "GAAATCGACGCCGACTTC",
      "TCGACGCCGACTTCGAC",
    ],
  },

  // Tetracycline resistance
  {
    id: "tetA",
    name: "tetA",
    description: "Tetracycline efflux protein",
    antibioticClass: ["tetracycline", "doxycycline"],
    mechanism: "Efflux pump",
    patterns: [
      "ATGAAAAAATTATTCATTGC",
      "AAAAAATTATTCATTGCAAC",
      "ATTATTCATTGCAACGAA",
    ],
  },
  {
    id: "tetR",
    name: "tetR",
    description: "Tetracycline repressor protein",
    antibioticClass: ["tetracycline"],
    mechanism: "Regulatory protein",
    patterns: [
      "ATGACCCAACAACGAAACCC",
      "CCCAACAACGAAACCCGC",
      "CAACGAAACCCGCCGCC",
    ],
  },

  // Trimethoprim resistance
  {
    id: "dfrA1",
    name: "dfrA1",
    description: "Dihydrofolate reductase",
    antibioticClass: ["trimethoprim"],
    mechanism: "Target replacement",
    patterns: [
      "ATGAATTGCCCAATATTATT",
      "AATTGCCCAATATTATTCG",
      "GCCCAATATTATTCGGTC",
    ],
  },

  // Colistin resistance
  {
    id: "mcr-1",
    name: "mcr-1",
    description: "Phosphoethanolamine transferase",
    antibioticClass: ["colistin"],
    mechanism: "Target modification",
    patterns: [
      "ATGAACAGTTTACTGAGCGC",
      "AACAGTTTACTGAGCGCAA",
      "GTTTACTGAGCGCAAGCC",
    ],
  },

  // Chloramphenicol resistance
  {
    id: "catA1",
    name: "catA1",
    description: "Chloramphenicol acetyltransferase",
    antibioticClass: ["chloramphenicol"],
    mechanism: "Enzymatic modification",
    patterns: [
      "ATGAGCGAAACCCTGTCTTC",
      "GCGAAACCCTGTCTTCGC",
      "AACCCTGTCTTCGCGGG",
    ],
  },

  // Fosfomycin resistance
  {
    id: "fosA",
    name: "fosA",
    description: "Fosfomycin resistance protein",
    antibioticClass: ["fosfomycin"],
    mechanism: "Enzymatic modification",
    patterns: [
      "ATGAACAAACTGAAAGAAGC",
      "AACAAACTGAAAGAAGCC",
      "AAACTGAAAGAAGCCGC",
    ],
  },
];

// Chromosomal mutations associated with resistance
export interface ChromosomalMutation {
  gene: string;
  position: number;
  wildType: string;
  mutant: string;
  antibiotics: string[];
  impact: number;
}

export const CHROMOSOMAL_MUTATIONS: ChromosomalMutation[] = [
  {
    gene: "gyrA",
    position: 83,
    wildType: "S",
    mutant: "L",
    antibiotics: ["ciprofloxacin", "levofloxacin"],
    impact: 0.85,
  },
  {
    gene: "parC",
    position: 80,
    wildType: "S",
    mutant: "I",
    antibiotics: ["ciprofloxacin"],
    impact: 0.72,
  },
  {
    gene: "rpoB",
    position: 531,
    wildType: "S",
    mutant: "L",
    antibiotics: ["rifampin"],
    impact: 0.95,
  },
];

// Antibiotic classification
export const ANTIBIOTIC_CLASSES = {
  "beta-lactams": ["ampicillin", "amoxicillin", "ceftriaxone", "meropenem"],
  aminoglycosides: ["gentamicin", "tobramycin", "amikacin"],
  quinolones: ["ciprofloxacin", "levofloxacin"],
  tetracyclines: ["tetracycline", "doxycycline"],
  "folate-inhibitors": ["trimethoprim"],
  polymyxins: ["colistin"],
  phenicols: ["chloramphenicol"],
  phosphonates: ["fosfomycin"],
};
