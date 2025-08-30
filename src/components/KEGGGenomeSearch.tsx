import React, { useState, useEffect } from "react";

// NCBI API Key
const NCBI_API_KEY = "feec4ac9f28178c8b078da5292d7caa86408";

// NCBI Datasets API base URL
const NCBI_DATASETS_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha";
import axios from "axios";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  Download,
  Database,
  Filter,
  RefreshCw,
  ExternalLink,
  Dna,
  Microscope,
  FileText,
  AlertCircle,
  CheckCircle,
  Play,
  Loader2,
  Sliders,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";

interface GenomeData {
  id: string;
  organism: string;
  species: string;
  strain?: string;
  variant?: string;
  taxonomy: string;
  size: number; // genome size in bp
  genes: number;
  proteins: number;
  description: string;
  source: "NCBI";

  ncbiId?: string;
  ncbiAccession?: string;
  gcContent?: number;
  sequenceAvailable: boolean;
}

interface GenomeSearchProps {
  onGenomeSelect?: (genome: GenomeData) => void;
  onSequenceDownload?: (genome: GenomeData) => void;
  onBatchProcess?: (genomes: GenomeData[]) => void;
  className?: string;
}

const GenomeSearch = ({
  onGenomeSelect = () => {},
  onSequenceDownload = () => {},
  onBatchProcess = () => {},
  className = "",
}: GenomeSearchProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpecies, setSelectedSpecies] = useState("all");
  const [selectedVariant, setSelectedVariant] = useState("all");
  const [selectedTaxonomy, setSelectedTaxonomy] = useState("all");
  const [genomes, setGenomes] = useState<GenomeData[]>([]);
  const [filteredGenomes, setFilteredGenomes] = useState<GenomeData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedGenomes, setSelectedGenomes] = useState<Set<string>>(
    new Set(),
  );
  const [activeTab, setActiveTab] = useState("search");

  // Additional filters
  const [sizeRange, setSizeRange] = useState<[number, number]>([0, 10]);
  const [geneCountRange, setGeneCountRange] = useState<[number, number]>([
    0, 10000,
  ]);
  const [gcContentRange, setGcContentRange] = useState<[number, number]>([
    20, 80,
  ]);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);

  // Fetch genome data from NCBI Datasets API
  const fetchGenomes = async () => {
    setIsLoading(true);
    setError("");

    try {
      // Using NCBI Datasets API with POST request as required by the API
      const response = await axios.post(
        `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        {
          filters: {
            assembly_source: "refseq",
            assembly_level: ["complete_genome"],
            exclude_paired_reports: true,
            exclude_atypical: true,
          },
          returned_content: "COMPLETE",
          page_size: 20,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "api-key": NCBI_API_KEY,
          },
        },
      );

      console.log("NCBI API Response:", response.data);

      if (!response.data) {
        throw new Error("No data received from NCBI Datasets API");
      }

      // Handle different response structures
      let reports = [];
      if (response.data.reports) {
        reports = response.data.reports;
      } else if (Array.isArray(response.data)) {
        reports = response.data;
      } else if (response.data.assemblies) {
        reports = response.data.assemblies;
      } else {
        console.warn("Unexpected response structure:", response.data);
        // Fallback to mock data for development
        reports = [
          {
            accession: "GCF_000005825.2",
            assembly_info: {
              assembly_accession: "GCF_000005825.2",
              assembly_name: "ASM582v2",
              assembly_stats: {
                total_sequence_length: 4641652,
                gc_percent: 66.6,
              },
            },
            organism: {
              organism_name: "Escherichia coli str. K-12 substr. MG1655",
              tax_id: 511145,
              infraspecific_names: {
                strain: "K-12",
              },
            },
            annotation_info: {
              stats: {
                gene_counts: {
                  total: 4140,
                  protein_coding: 4140,
                },
              },
            },
          },
          {
            accession: "GCF_000393015.1",
            assembly_info: {
              assembly_accession: "GCF_000393015.1",
              assembly_name: "ASM39301v1",
              assembly_stats: {
                total_sequence_length: 6264404,
                gc_percent: 67.1,
              },
            },
            organism: {
              organism_name: "Pseudomonas aeruginosa PAO1",
              tax_id: 208964,
              infraspecific_names: {
                strain: "PAO1",
              },
            },
            annotation_info: {
              stats: {
                gene_counts: {
                  total: 5570,
                  protein_coding: 5570,
                },
              },
            },
          },
        ];
      }

      // Process genome reports from Datasets API
      const genomeDetails = reports.map((report: any) => {
        const assembly = report.assembly_info || {};
        const organism = report.organism || {};
        const annotation = report.annotation_info || {};
        const assemblyStats = assembly.assembly_stats || {};

        return {
          id: assembly.assembly_accession || report.accession,
          organism: organism.organism_name || "Unknown organism",
          species:
            organism.organism_name?.split(" ").slice(0, 2).join(" ") ||
            "Unknown species",
          strain: organism.infraspecific_names?.strain || undefined,
          taxonomy: organism.tax_id ? `Tax ID: ${organism.tax_id}` : "Bacteria",
          size: assemblyStats.total_sequence_length || 0,
          genes: annotation.stats?.gene_counts?.total || 0,
          proteins: annotation.stats?.gene_counts?.protein_coding || 0,
          description:
            assembly.assembly_name ||
            organism.organism_name ||
            "Bacterial genome",
          source: "NCBI",
          ncbiId: report.accession,
          ncbiAccession: assembly.assembly_accession || report.accession,
          gcContent: assemblyStats.gc_percent || 50,
          sequenceAvailable: true,
        };
      });

      const validGenomes = genomeDetails.filter(Boolean) as GenomeData[];

      if (validGenomes.length === 0) {
        throw new Error("No valid genomes found");
      }

      setGenomes(validGenomes);
      setFilteredGenomes(validGenomes);

      // Set filter ranges based on actual data
      const sizes = validGenomes.map((g: GenomeData) => g.size / 1000000); // Convert to Mbp
      const genes = validGenomes.map((g: GenomeData) => g.genes);
      const gcContents = validGenomes
        .map((g: GenomeData) => g.gcContent)
        .filter(Boolean);

      setSizeRange([Math.min(...sizes), Math.max(...sizes)]);
      setGeneCountRange([Math.min(...genes), Math.max(...genes)]);
      setGcContentRange([Math.min(...gcContents), Math.max(...gcContents)]);
    } catch (err: any) {
      console.error("Error fetching NCBI genomes:", err);

      // More detailed error handling
      if (err.response) {
        console.error("Response status:", err.response.status);
        console.error("Response data:", err.response.data);
        setError(
          `API Error ${err.response.status}: ${err.response.data?.message || "Failed to fetch genome data from NCBI Datasets API"}`,
        );
      } else if (err.request) {
        console.error("No response received:", err.request);
        setError("Network error: Unable to connect to NCBI Datasets API");
      } else {
        console.error("Request setup error:", err.message);
        setError(`Request error: ${err.message}`);
      }

      setGenomes([]);
      setFilteredGenomes([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch genomes on component mount
  useEffect(() => {
    fetchGenomes();
  }, []);

  useEffect(() => {
    // Filter genomes based on search criteria and advanced filters
    let filtered = genomes.filter((genome) => {
      const matchesQuery =
        searchQuery === "" ||
        genome.organism.toLowerCase().includes(searchQuery.toLowerCase()) ||
        genome.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        genome.species.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (genome.strain &&
          genome.strain.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (genome.variant &&
          genome.variant.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesSpecies =
        selectedSpecies === "all" ||
        genome.species.toLowerCase().includes(selectedSpecies.toLowerCase());

      const matchesVariant =
        selectedVariant === "all" ||
        (genome.variant &&
          genome.variant.toLowerCase().includes(selectedVariant.toLowerCase()));

      const matchesTaxonomy =
        selectedTaxonomy === "all" ||
        genome.taxonomy.toLowerCase().includes(selectedTaxonomy.toLowerCase());

      // Advanced filters
      const genomeSizeMbp = genome.size / 1000000;
      const matchesSize =
        genomeSizeMbp >= sizeRange[0] && genomeSizeMbp <= sizeRange[1];

      const matchesGeneCount =
        genome.genes >= geneCountRange[0] && genome.genes <= geneCountRange[1];

      const matchesGcContent =
        !genome.gcContent || // Don't filter if GC content is unknown
        (genome.gcContent >= gcContentRange[0] &&
          genome.gcContent <= gcContentRange[1]);

      return (
        matchesQuery &&
        matchesSpecies &&
        matchesVariant &&
        matchesTaxonomy &&
        matchesSize &&
        matchesGeneCount &&
        matchesGcContent
      );
    });

    setFilteredGenomes(filtered);
  }, [
    searchQuery,
    selectedSpecies,
    selectedVariant,
    selectedTaxonomy,
    sizeRange,
    geneCountRange,
    gcContentRange,
    genomes,
  ]);

  const handleGenomeSelect = (genome: GenomeData) => {
    const newSelected = new Set(selectedGenomes);
    if (newSelected.has(genome.id)) {
      newSelected.delete(genome.id);
    } else {
      newSelected.add(genome.id);
    }
    setSelectedGenomes(newSelected);
    onGenomeSelect(genome);
  };

  const handleSequenceDownload = async (genome: GenomeData) => {
    setIsLoading(true);
    try {
      // Download CDS FASTA directly using GET request
      const response = await axios.get(
        `${NCBI_DATASETS_BASE_URL}/genome/accession/${genome.ncbiAccession || genome.id}/download`,
        {
          params: {
            include_annotation_type: ["CDS_FASTA"],
            filename: `${genome.ncbiAccession || genome.id}_cds.fasta`,
          },
          responseType: "blob",
          headers: {
            Accept: "application/octet-stream",
            "api-key": NCBI_API_KEY,
          },
        },
      );

      // Check if we got a valid response
      if (response.data.size === 0) {
        throw new Error("Empty file received");
      }

      // Create and download the CDS FASTA file
      const blob = new Blob([response.data], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${genome.ncbiAccession || genome.id}_cds.fasta`;
      a.click();
      URL.revokeObjectURL(url);

      onSequenceDownload(genome);
    } catch (error: any) {
      console.error("Error downloading CDS sequence:", error);

      // Fallback: try to download genome FASTA if CDS fails
      try {
        const fallbackResponse = await axios.get(
          `${NCBI_DATASETS_BASE_URL}/genome/accession/${genome.ncbiAccession || genome.id}/download`,
          {
            params: {
              include_annotation_type: ["GENOME_FASTA"],
              filename: `${genome.ncbiAccession || genome.id}_genome.fasta`,
            },
            responseType: "blob",
            headers: {
              Accept: "application/octet-stream",
              "api-key": NCBI_API_KEY,
            },
          },
        );

        const blob = new Blob([fallbackResponse.data], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${genome.ncbiAccession || genome.id}_genome.fasta`;
        a.click();
        URL.revokeObjectURL(url);

        onSequenceDownload(genome);
      } catch (fallbackError: any) {
        console.error("Fallback download also failed:", fallbackError);
        if (error.response) {
          setError(
            `Download failed: ${error.response.status} - ${error.response.data?.message || "Unable to download sequence"}`,
          );
        } else {
          setError(
            "Failed to download sequence from NCBI Datasets API. The API might be temporarily unavailable.",
          );
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleBatchProcess = async () => {
    if (selectedGenomes.size === 0) {
      setError("Please select at least one genome for batch processing");
      return;
    }

    setIsBatchProcessing(true);
    setError("");

    try {
      // Get selected genome objects
      const genomesToProcess = genomes.filter((g) => selectedGenomes.has(g.id));

      // Download FASTA sequences for each selected genome using NCBI Datasets API
      const genomesWithSequences = await Promise.all(
        genomesToProcess.map(async (genome) => {
          try {
            // Using NCBI Datasets API to get CDS FASTA sequence
            const response = await axios.get(
              `${NCBI_DATASETS_BASE_URL}/genome/accession/${genome.ncbiAccession || genome.id}/download`,
              {
                params: {
                  include_annotation_type: ["CDS_FASTA"],
                  filename: `${genome.ncbiAccession || genome.id}_cds.fasta`,
                },
                responseType: "text",
                headers: {
                  Accept: "text/plain",
                  "api-key": NCBI_API_KEY,
                },
              },
            );

            // Store the CDS FASTA content directly
            return {
              ...genome,
              fastaContent: response.data,
              isZipFormat: false,
              fileType: "CDS_FASTA",
            };
          } catch (error) {
            console.error(`Error fetching sequence for ${genome.id}:`, error);
            return null;
          }
        }),
      );

      const validGenomesWithSequences = genomesWithSequences.filter(Boolean);

      if (validGenomesWithSequences.length === 0) {
        throw new Error("Failed to fetch sequences for selected genomes");
      }

      // Call the batch processing function with genomes that have sequences
      onBatchProcess(validGenomesWithSequences);
    } catch (error) {
      console.error("Batch processing error:", error);
      setError("Failed to process genomes in batch mode: " + error.message);
    } finally {
      setIsBatchProcessing(false);
    }
  };

  // Function to search for genomes by query using NCBI Datasets API
  const searchGenomesByQuery = async (query: string) => {
    setIsLoading(true);
    setError("");

    try {
      // Using NCBI Datasets API for search with POST request
      const response = await axios.post(
        `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        {
          filters: {
            assembly_source: "refseq",
            assembly_level: ["complete_genome"],
            search_text: query,
            exclude_paired_reports: true,
            exclude_atypical: true,
          },
          returned_content: "COMPLETE",
          page_size: 20,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "api-key": NCBI_API_KEY,
          },
        },
      );

      console.log("Search API Response:", response.data);

      if (!response.data) {
        throw new Error("No data received from NCBI Datasets API");
      }

      // Handle different response structures
      let searchReports = [];
      if (response.data.reports) {
        searchReports = response.data.reports;
      } else if (Array.isArray(response.data)) {
        searchReports = response.data;
      } else if (response.data.assemblies) {
        searchReports = response.data.assemblies;
      } else {
        console.warn("No matching genomes found for query:", query);
        setError("No genomes found matching your search criteria");
        setGenomes([]);
        setFilteredGenomes([]);
        return;
      }

      if (searchReports.length === 0) {
        setError("No genomes found matching your search criteria");
        setGenomes([]);
        setFilteredGenomes([]);
        return;
      }

      // Process genome reports from Datasets API
      const genomeDetails = searchReports.map((report: any) => {
        const assembly = report.assembly_info || {};
        const organism = report.organism || {};
        const annotation = report.annotation_info || {};
        const assemblyStats = assembly.assembly_stats || {};

        return {
          id: assembly.assembly_accession || report.accession,
          organism: organism.organism_name || "Unknown organism",
          species:
            organism.organism_name?.split(" ").slice(0, 2).join(" ") ||
            "Unknown species",
          strain: organism.infraspecific_names?.strain || undefined,
          taxonomy: organism.tax_id ? `Tax ID: ${organism.tax_id}` : "Bacteria",
          size: assemblyStats.total_sequence_length || 0,
          genes: annotation.stats?.gene_counts?.total || 0,
          proteins: annotation.stats?.gene_counts?.protein_coding || 0,
          description:
            assembly.assembly_name ||
            organism.organism_name ||
            "Bacterial genome",
          source: "NCBI",
          ncbiId: report.accession,
          ncbiAccession: assembly.assembly_accession || report.accession,
          gcContent: assemblyStats.gc_percent || 50,
          sequenceAvailable: true,
        };
      });

      const validGenomes = genomeDetails.filter(Boolean) as GenomeData[];

      setGenomes(validGenomes);
      setFilteredGenomes(validGenomes);
    } catch (error: any) {
      console.error("Error searching genomes:", error);
      if (error.response) {
        setError(
          `Search failed: ${error.response.status} - ${error.response.data?.message || "Unable to search genomes"}`,
        );
      } else {
        setError(
          "Failed to search genomes using NCBI Datasets API. Please try again later.",
        );
      }
      setGenomes([]);
      setFilteredGenomes([]);
    } finally {
      setIsLoading(false);
    }
  };

  const getUniqueValues = (key: keyof GenomeData) => {
    const values = genomes
      .map((genome) => genome[key])
      .filter((value) => value !== undefined && value !== null)
      .map((value) => String(value));
    return [...new Set(values)].sort();
  };

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedSpecies("all");
    setSelectedVariant("all");
    setSelectedTaxonomy("all");
  };

  return (
    <Card
      className={`w-full bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 shadow-lg ${className}`}
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-2xl font-bold flex items-center text-blue-900">
              <Database className="mr-2 h-6 w-6" />
              NCBI Datasets API Genome Search
            </CardTitle>
            <CardDescription className="text-blue-700">
              Search and access bacterial genomes from NCBI datasets for
              antibiotic resistance analysis
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="bg-blue-100 text-blue-800">
              {filteredGenomes.length} genomes
            </Badge>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      window.open(
                        "https://www.ncbi.nlm.nih.gov/datasets/genome/",
                        "_blank",
                      )
                    }
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Visit NCBI Genome Database</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-6 flex justify-center">
          <div className="inline-flex items-center rounded-lg border border-blue-200 bg-white p-1">
            <div className="px-4 py-2 rounded-md bg-blue-100 text-blue-800 font-medium">
              NCBI Datasets API v2alpha
            </div>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="search" className="flex items-center">
              <Search className="mr-2 h-4 w-4" />
              Search & Filter
            </TabsTrigger>
            <TabsTrigger value="selected" className="flex items-center">
              <CheckCircle className="mr-2 h-4 w-4" />
              Selected ({selectedGenomes.size})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="space-y-6">
            {/* Search and Filter Section */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-white rounded-lg border border-blue-200">
                <div className="space-y-2">
                  <Label htmlFor="search" className="text-sm font-medium">
                    Search
                  </Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="search"
                      placeholder="Search by ID, organism, strain..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          searchGenomesByQuery(searchQuery);
                        }
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="species" className="text-sm font-medium">
                    Species
                  </Label>
                  <Select
                    value={selectedSpecies}
                    onValueChange={setSelectedSpecies}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All species" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All species</SelectItem>
                      {getUniqueValues("species").map((species) => (
                        <SelectItem key={species} value={species}>
                          {species}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="variant" className="text-sm font-medium">
                    Variant/Strain
                  </Label>
                  <Select
                    value={selectedVariant}
                    onValueChange={setSelectedVariant}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All variants" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All variants</SelectItem>
                      {getUniqueValues("variant").map((variant) => (
                        <SelectItem key={variant} value={variant}>
                          {variant}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="taxonomy" className="text-sm font-medium">
                    Taxonomy
                  </Label>
                  <Select
                    value={selectedTaxonomy}
                    onValueChange={setSelectedTaxonomy}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All taxonomy" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All taxonomy</SelectItem>
                      <SelectItem value="proteobacteria">
                        Proteobacteria
                      </SelectItem>
                      <SelectItem value="firmicutes">Firmicutes</SelectItem>
                      <SelectItem value="enterobacterales">
                        Enterobacterales
                      </SelectItem>
                      <SelectItem value="pseudomonadales">
                        Pseudomonadales
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Advanced Filters */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="advanced-filters"
                    checked={showAdvancedFilters}
                    onCheckedChange={setShowAdvancedFilters}
                  />
                  <Label
                    htmlFor="advanced-filters"
                    className="cursor-pointer flex items-center"
                  >
                    <Sliders className="h-4 w-4 mr-1" />
                    Advanced Filters
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                    className="flex items-center"
                  >
                    <Filter className="mr-2 h-4 w-4" />
                    Clear Filters
                  </Button>

                  {selectedGenomes.size > 0 && (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleBatchProcess}
                      disabled={isBatchProcessing || selectedGenomes.size === 0}
                      className="flex items-center"
                    >
                      {isBatchProcessing ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Process {selectedGenomes.size} Genomes
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </div>

              {showAdvancedFilters && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 bg-white rounded-lg border border-blue-200">
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <Label className="text-sm font-medium">
                        Genome Size (Mbp)
                      </Label>
                      <span className="text-xs text-gray-500">
                        {sizeRange[0].toFixed(1)} - {sizeRange[1].toFixed(1)}{" "}
                        Mbp
                      </span>
                    </div>
                    <Slider
                      min={0}
                      max={10}
                      step={0.1}
                      value={sizeRange}
                      onValueChange={(value) =>
                        setSizeRange(value as [number, number])
                      }
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <Label className="text-sm font-medium">Gene Count</Label>
                      <span className="text-xs text-gray-500">
                        {geneCountRange[0]} - {geneCountRange[1]}
                      </span>
                    </div>
                    <Slider
                      min={0}
                      max={10000}
                      step={100}
                      value={geneCountRange}
                      onValueChange={(value) =>
                        setGeneCountRange(value as [number, number])
                      }
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <Label className="text-sm font-medium">
                        GC Content (%)
                      </Label>
                      <span className="text-xs text-gray-500">
                        {gcContentRange[0]}% - {gcContentRange[1]}%
                      </span>
                    </div>
                    <Slider
                      min={20}
                      max={80}
                      step={1}
                      value={gcContentRange}
                      onValueChange={(value) =>
                        setGcContentRange(value as [number, number])
                      }
                      className="w-full"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                    className="flex items-center"
                  >
                    <Filter className="mr-2 h-4 w-4" />
                    Clear Filters
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => searchGenomesByQuery(searchQuery)}
                    className="flex items-center"
                    disabled={isLoading}
                  >
                    <Search className="mr-2 h-4 w-4" />
                    Search NCBI
                  </Button>
                </div>
                {isLoading && (
                  <div className="flex items-center text-sm text-gray-600">
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Loading genomes...
                  </div>
                )}
              </div>
              <div className="text-sm text-gray-600">
                Showing {filteredGenomes.length} of {genomes.length} genomes
              </div>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Genomes Table */}
            <div className="border rounded-lg bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Select</TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>Organism</TableHead>
                    <TableHead>Strain/Variant</TableHead>
                    <TableHead>Size (Mbp)</TableHead>
                    <TableHead>GC%</TableHead>
                    <TableHead>Genes</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredGenomes.map((genome) => (
                    <TableRow key={genome.id} className="hover:bg-blue-50">
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedGenomes.has(genome.id)}
                          onChange={() => handleGenomeSelect(genome)}
                          className="rounded border-gray-300"
                        />
                      </TableCell>
                      <TableCell className="font-mono font-medium text-blue-700">
                        {genome.id}
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{genome.organism}</div>
                          <div className="text-sm text-gray-500">
                            {genome.species}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {genome.strain && (
                            <div className="font-medium">{genome.strain}</div>
                          )}
                          {genome.variant && (
                            <div className="text-gray-600">
                              {genome.variant}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">
                        {(genome.size / 1000000).toFixed(2)}
                      </TableCell>
                      <TableCell className="font-mono">
                        {genome.gcContent?.toFixed(1) || "N/A"}
                      </TableCell>
                      <TableCell className="font-mono">
                        {genome.genes.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleSequenceDownload(genome)}
                                  disabled={
                                    !genome.sequenceAvailable || isLoading
                                  }
                                >
                                  <Download className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Download CDS FASTA sequence</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    if (genome.ncbiAccession) {
                                      window.open(
                                        `https://www.ncbi.nlm.nih.gov/datasets/genome/${genome.ncbiAccession}`,
                                        "_blank",
                                      );
                                    }
                                  }}
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>View in NCBI database</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="selected" className="space-y-4">
            {selectedGenomes.size === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Microscope className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>No genomes selected</p>
                <p className="text-sm">
                  Select genomes from the search tab to view them here
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold">
                    Selected Genomes ({selectedGenomes.size})
                  </h3>
                  <Button
                    variant="outline"
                    onClick={() => setSelectedGenomes(new Set())}
                  >
                    Clear Selection
                  </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Array.from(selectedGenomes).map((genomeId) => {
                    const genome = genomes.find((g) => g.id === genomeId);
                    if (!genome) return null;
                    return (
                      <Card key={genome.id} className="border-blue-200">
                        <CardHeader className="pb-2">
                          <div className="flex justify-between items-start">
                            <div>
                              <CardTitle className="text-lg">
                                {genome.organism}
                              </CardTitle>
                              <CardDescription>
                                {genome.id} • {genome.species}
                              </CardDescription>
                            </div>
                            <Badge variant="outline">{genome.id}</Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span>Size:</span>
                              <span className="font-mono">
                                {(genome.size / 1000000).toFixed(2)} Mbp
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>GC Content:</span>
                              <span className="font-mono">
                                {genome.gcContent?.toFixed(1) || "N/A"}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Genes:</span>
                              <span className="font-mono">
                                {genome.genes.toLocaleString()}
                              </span>
                            </div>
                            <div className="pt-2">
                              <p className="text-xs text-gray-600">
                                {genome.description}
                              </p>
                            </div>
                          </div>
                          <div className="flex space-x-2 mt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSequenceDownload(genome)}
                              className="flex-1"
                            >
                              <Download className="mr-2 h-4 w-4" />
                              Download CDS
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                if (genome.ncbiAccession) {
                                  window.open(
                                    `https://www.ncbi.nlm.nih.gov/datasets/genome/${genome.ncbiAccession}`,
                                    "_blank",
                                  );
                                }
                              }}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default GenomeSearch;
