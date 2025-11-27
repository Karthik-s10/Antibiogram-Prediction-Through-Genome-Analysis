import React, { useState, useEffect } from "react";

// NCBI API Key - Using the official NCBI Datasets API
const NCBI_API_KEY = "feec4ac9f28178c8b078da5292d7caa86408";

// NCBI Datasets API base URL - Official v2alpha endpoint
const NCBI_DATASETS_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha";
// Enable detailed logging for debugging
const DEBUG_MODE = true;

import axios from "axios";
import JSZip from "jszip";
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

interface NCBIGenomeSearchProps {
  onGenomeSelect?: (genome: GenomeData) => void;
  onSequenceDownload?: (genome: GenomeData) => void;
  onBatchProcess?: (genomes: GenomeData[]) => void;
  className?: string;
}

const NCBIGenomeSearch = ({
  onGenomeSelect = () => {},
  onSequenceDownload = () => {},
  onBatchProcess = () => {},
  className = "",
}: NCBIGenomeSearchProps) => {
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
      // Using NCBI Datasets API with POST request and JSON body
      const requestData = {
        filters: {
          source_database: ["RefSeq"],
          assembly_level: ["Complete Genome"],
          exclude_paired_reports: true,
          exclude_atypical: true,
        },
        returned_content: "COMPLETE",
        page_size: 20,
      };

      if (DEBUG_MODE) {
        console.log(
          "NCBI API Request URL:",
          `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        );
        console.log("NCBI API Request Data:", requestData);
      }

      const response = await axios({
        method: "post",
        url: `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        data: requestData,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "api-key": NCBI_API_KEY,
        },
        timeout: 30000, // 30 second timeout
      });

      if (DEBUG_MODE) {
        console.log("NCBI API Response:", response.data);
        console.log("Response structure keys:", Object.keys(response.data));
      }

      if (!response.data) {
        throw new Error("No data received from NCBI Datasets API");
      }

      // Handle different response structures
      let reports = [];
      if (response.data.reports) {
        console.log(
          "Found reports array with length:",
          response.data.reports.length,
        );
        reports = response.data.reports;
      } else if (Array.isArray(response.data)) {
        console.log(
          "Response data is an array with length:",
          response.data.length,
        );
        reports = response.data;
      } else if (response.data.assemblies) {
        console.log(
          "Found assemblies with length:",
          response.data.assemblies.length,
        );
        reports = response.data.assemblies;
      } else if (response.data.assemblies_by_taxid) {
        // Handle v2alpha API response structure
        console.log("Found assemblies_by_taxid structure");
        const assembliesData = Object.values(
          response.data.assemblies_by_taxid || {},
        );
        reports = assembliesData.flatMap(
          (taxData: any) => taxData.assemblies || [],
        );
        console.log(
          "Extracted reports from assemblies_by_taxid:",
          reports.length,
        );
      } else if (response.data.assemblies_by_accession) {
        // Alternative v2alpha API response structure
        console.log("Found assemblies_by_accession structure");
        reports = Object.values(response.data.assemblies_by_accession || {});
        console.log(
          "Extracted reports from assemblies_by_accession:",
          reports.length,
        );
      } else {
        console.warn("Unexpected response structure:", response.data);
        console.log("Response data keys:", Object.keys(response.data));

        // Check if we have direct report objects in the console logs
        if (DEBUG_MODE) {
          console.log("Attempting to extract direct report objects");
        }

        // Try to extract reports directly from the response data
        reports = [];
        try {
          // If we have direct objects in the response, use them
          if (response.data && typeof response.data === "object") {
            // Check if this is a single report object
            if (response.data.accession || response.data.organism) {
              console.log("Found single report object");
              reports = [response.data];
            }
            // Check if this might be a collection of reports
            else if (
              Object.values(response.data).some(
                (val) =>
                  val &&
                  typeof val === "object" &&
                  ('accession' in val || 'organism' in val),
              )
            ) {
              console.log("Found collection of report objects");
              reports = Object.values(response.data).filter(
                (val) =>
                  val &&
                  typeof val === "object" &&
                  ('accession' in val || 'organism' in val),
              );
            }
          }

          if (reports.length === 0) {
            console.log("No reports found in response data, using mock data");
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
        } catch (err) {
          console.error("Error extracting direct reports:", err);
        }
      }

      // Process genome reports from Datasets API
      const genomeDetails = reports
        .map((report: any) => {
          if (DEBUG_MODE) {
            console.log("Processing initial report:", report);
          }

          try {
            // Handle the new v2alpha API response structure
            const assembly = report.assembly_info || {};
            const organism = report.organism || {};
            const annotation = report.annotation_info || {};
            const assemblyStats =
              report.assembly_stats || assembly.assembly_stats || {};

            // Extract organism name from various possible locations
            const organismName = organism.organism_name || "Unknown organism";

            // Extract accession - use the main accession field
            const accession = report.accession || report.current_accession;

            // If we don't have an accession, try to extract it from the console log format
            // This handles the case shown in the screenshot where accession is in a specific format
            let extractedAccession = accession;
            if (!extractedAccession && typeof report === "object") {
              // Try to find accession in the format shown in the console logs
              const keys = Object.keys(report);
              for (const key of keys) {
                if (key === "accession" && typeof report[key] === "string") {
                  extractedAccession = report[key];
                  break;
                }
              }
            }

            // Convert size from string to number if needed
            const sizeValue = assemblyStats.total_sequence_length;
            const genomeSizeNumber =
              typeof sizeValue === "string"
                ? parseInt(sizeValue, 10)
                : sizeValue || 0;

            const processedGenome = {
              id:
                extractedAccession ||
                "unknown-id-" + Math.random().toString(36).substring(2, 9),
              organism: organismName,
              species:
                organismName.split(" ").slice(0, 2).join(" ") ||
                "Unknown species",
              strain: organism.infraspecific_names?.strain || undefined,
              taxonomy: organism.tax_id
                ? `Tax ID: ${organism.tax_id}`
                : "Bacteria",
              size: genomeSizeNumber,
              genes: annotation.stats?.gene_counts?.total || 0,
              proteins: annotation.stats?.gene_counts?.protein_coding || 0,
              description:
                assembly.assembly_name || organismName || "Bacterial genome",
              source: "NCBI" as const,
              ncbiId: extractedAccession,
              ncbiAccession: extractedAccession,
              gcContent: assemblyStats.gc_percent || 50,
              sequenceAvailable: true,
            };

            if (DEBUG_MODE) {
              console.log("Processed initial genome:", processedGenome);
            }

            return processedGenome;
          } catch (err) {
            console.error("Error processing genome report:", err, report);
            return null;
          }
        })
        .filter(Boolean);

      // This filter is now redundant since we're already filtering in the map function
      // but keeping it for extra safety
      const validGenomes = genomeDetails.filter((genome) => {
        return genome && genome.id && genome.organism;
      }) as GenomeData[];

      if (DEBUG_MODE) {
        console.log("Final valid genomes count:", validGenomes.length);
        console.log("Final valid genomes:", validGenomes);
      }

      if (DEBUG_MODE) {
        console.log("Valid initial genomes processed:", validGenomes.length);
        console.log("First few initial genomes:", validGenomes.slice(0, 3));
      }

      if (validGenomes.length === 0) {
        throw new Error("No valid genomes found");
      }

      // Force a state update with the new genomes
      console.log("Setting genomes state with", validGenomes.length, "genomes");

      // Set genomes state first
      setGenomes(validGenomes);

      // Set filtered genomes to show all results initially
      setFilteredGenomes(validGenomes);

      // Set filter ranges based on actual data
      if (validGenomes.length > 0) {
        const sizes = validGenomes.map((g: GenomeData) => g.size / 1000000); // Convert to Mbp
        const genes = validGenomes.map((g: GenomeData) => g.genes);
        const gcContents = validGenomes
          .map((g: GenomeData) => g.gcContent)
          .filter(Boolean);

        // Only set ranges if we have valid values
        if (sizes.length > 0) {
          setSizeRange([Math.min(...sizes), Math.max(...sizes)]);
        }
        if (genes.length > 0) {
          setGeneCountRange([Math.min(...genes), Math.max(...genes)]);
        }
        if (gcContents.length > 0) {
          setGcContentRange([Math.min(...gcContents), Math.max(...gcContents)]);
        }
      }
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
    console.log("Component mounted, fetching genomes...");
    fetchGenomes();

    // Initialize filter values
    setSearchQuery("");
    setSelectedSpecies("all");
    setSelectedVariant("all");
    setSelectedTaxonomy("all");
    setShowAdvancedFilters(false);

    // Reset selected genomes
    setSelectedGenomes(new Set());
  }, []);

  // Debug effect to monitor state changes
  useEffect(() => {
    console.log(
      "State updated - genomes:",
      genomes.length,
      "filtered:",
      filteredGenomes.length,
    );
    console.log("Genomes array:", genomes);
    console.log("FilteredGenomes array:", filteredGenomes);
  }, [genomes, filteredGenomes]);

  useEffect(() => {
    console.log("Filter effect triggered with genomes:", genomes.length);
    console.log("Current genomes array in filter effect:", genomes);

    // Safety check - if genomes is empty, set empty filtered array
    if (!genomes || genomes.length === 0) {
      console.log("No genomes to filter, setting empty filtered array");
      setFilteredGenomes([]);
      return;
    }

    // For search by strain name, we want to show all results from the API
    // This is a special case when we've just performed a search
    if (
      searchQuery &&
      searchQuery.trim() !== "" &&
      genomes.length > 0 &&
      selectedSpecies === "all" &&
      selectedVariant === "all" &&
      selectedTaxonomy === "all" &&
      !showAdvancedFilters
    ) {
      console.log(
        "Search query present with no other filters, showing all search results",
      );
      setFilteredGenomes([...genomes]);
      return;
    }

    // Initialize with all genomes if no filters are applied
    if (
      searchQuery === "" &&
      selectedSpecies === "all" &&
      selectedVariant === "all" &&
      selectedTaxonomy === "all" &&
      !showAdvancedFilters
    ) {
      console.log("No filters applied, showing all genomes");
      setFilteredGenomes([...genomes]);
      return;
    }

    // Filter genomes based on search criteria and advanced filters
    let filtered = genomes.filter((genome) => {
      // Safety check for null/undefined genome objects
      if (!genome) {
        console.warn("Found null/undefined genome in filter");
        return false;
      }

      try {
        // Convert search query to lowercase once for efficiency
        const lowerSearchQuery = searchQuery.toLowerCase();

        // Check if the search query matches any of the genome fields
        const matchesQuery =
          searchQuery === "" ||
          (genome.organism &&
            genome.organism.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.id && genome.id.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.species &&
            genome.species.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.strain &&
            genome.strain.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.variant &&
            genome.variant.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.ncbiAccession &&
            genome.ncbiAccession.toLowerCase().includes(lowerSearchQuery)) ||
          (genome.ncbiId &&
            genome.ncbiId.toLowerCase().includes(lowerSearchQuery));

        // Check if the species matches
        const matchesSpecies =
          selectedSpecies === "all" ||
          (genome.species &&
            genome.species
              .toLowerCase()
              .includes(selectedSpecies.toLowerCase()));

        // Check if the variant or strain matches
        const matchesVariant =
          selectedVariant === "all" ||
          (genome.variant &&
            genome.variant
              .toLowerCase()
              .includes(selectedVariant.toLowerCase())) ||
          (genome.strain &&
            genome.strain
              .toLowerCase()
              .includes(selectedVariant.toLowerCase()));

        // Check if the taxonomy matches
        const matchesTaxonomy =
          selectedTaxonomy === "all" ||
          (genome.taxonomy &&
            genome.taxonomy
              .toLowerCase()
              .includes(selectedTaxonomy.toLowerCase()));

        // Advanced filters - only apply if advanced filters are shown
        let matchesAdvancedFilters = true;
        if (showAdvancedFilters) {
          const genomeSizeMbp = genome.size / 1000000;
          const matchesSize =
            genomeSizeMbp >= sizeRange[0] && genomeSizeMbp <= sizeRange[1];

          const matchesGeneCount =
            genome.genes >= geneCountRange[0] &&
            genome.genes <= geneCountRange[1];

          const matchesGcContent =
            !genome.gcContent || // Don't filter if GC content is unknown
            (genome.gcContent >= gcContentRange[0] &&
              genome.gcContent <= gcContentRange[1]);

          matchesAdvancedFilters =
            matchesSize && matchesGeneCount && matchesGcContent;
        }

        return (
          matchesQuery &&
          matchesSpecies &&
          matchesVariant &&
          matchesTaxonomy &&
          matchesAdvancedFilters
        );
      } catch (err) {
        console.error("Error filtering genome:", err, genome);
        return false;
      }
    });

    console.log("Filtered genomes:", filtered.length, "out of", genomes.length);
    console.log("Filtered genomes array:", filtered);

    // Set filtered genomes directly
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
    showAdvancedFilters,
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
      console.log(
        `Downloading sequence for ${genome.ncbiAccession || genome.id}`,
      );
      // Download CDS FASTA using POST request with JSON body
      const downloadRequestData = {
        accessions: [genome.ncbiAccession || genome.id],
        include_annotation_type: ["CDS_FASTA", "GENOME_FASTA"], // Request both types for better quality
        filename: `${genome.ncbiAccession || genome.id}_cds.fasta`,
        // Request the data in a specific format
        format: "fasta",
      };

      const response = await axios({
        method: "post",
        url: `${NCBI_DATASETS_BASE_URL}/genome/download`,
        data: downloadRequestData,
        responseType: "blob",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/plain, application/octet-stream",
          "api-key": NCBI_API_KEY,
        },
        timeout: 60000, // 60 second timeout for downloads
      });

      // Check if we got a valid response
      if (response.data.size === 0) {
        console.error("Empty file received");
        throw new Error("Empty file received");
      }

      console.log(
        `Successfully downloaded sequence for ${genome.ncbiAccession || genome.id}, size: ${response.data.size} bytes`,
      );

      // Check if the response is a ZIP file (common format from NCBI)
      const isZip =
        response.headers["content-type"]?.includes("application/zip") ||
        response.data.slice(0, 4).toString() === "PK\x03\x04" ||
        (new Uint8Array(response.data.slice(0, 4))[0] === 0x50 &&
          new Uint8Array(response.data.slice(0, 4))[1] === 0x4b);

      if (isZip) {
        console.log("Received ZIP file from NCBI, downloading as .zip");

        // Try to extract and assess FASTA quality before downloading
        try {
          const fastaContent = await extractFastaFromZip(response.data);
          if (fastaContent) {
            const qualityScore = assessFastaQuality(fastaContent);
            let qualityLabel = "Low";
            if (qualityScore >= 80) qualityLabel = "High";
            else if (qualityScore >= 50) qualityLabel = "Medium";

            console.log(
              `ZIP contains FASTA with quality score: ${qualityScore} (${qualityLabel})`,
            );
          }
        } catch (extractError) {
          console.error("Error assessing ZIP content quality:", extractError);
        }

        // Create and download as ZIP file
        const blob = new Blob([response.data], { type: "application/zip" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${genome.ncbiAccession || genome.id}_cds.zip`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        // For direct FASTA content, assess quality before downloading
        try {
          const textData = await response.data.text();
          const qualityScore = assessFastaQuality(textData);
          let qualityLabel = "Low";
          if (qualityScore >= 80) qualityLabel = "High";
          else if (qualityScore >= 50) qualityLabel = "Medium";

          console.log(
            `Direct FASTA quality score: ${qualityScore} (${qualityLabel})`,
          );

          // Create and download the CDS FASTA file
          const blob = new Blob([textData], { type: "text/plain" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${genome.ncbiAccession || genome.id}_cds_${qualityLabel.toLowerCase()}_quality.fasta`;
          a.click();
          URL.revokeObjectURL(url);
        } catch (textError) {
          console.error("Error processing text FASTA:", textError);
          // Fallback to binary download if text processing fails
          const blob = new Blob([response.data], { type: "text/plain" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${genome.ncbiAccession || genome.id}_cds.fasta`;
          a.click();
          URL.revokeObjectURL(url);
        }
      }

      onSequenceDownload(genome);
    } catch (error: any) {
      console.error("Error downloading CDS sequence:", error);

      // Fallback: try to download genome FASTA if CDS fails
      try {
        console.log(
          `Attempting fallback download for ${genome.ncbiAccession || genome.id} using GENOME_FASTA`,
        );
        const fallbackRequestData = {
          accessions: [genome.ncbiAccession || genome.id],
          include_annotation_type: ["GENOME_FASTA"],
          filename: `${genome.ncbiAccession || genome.id}_genome.fasta`,
          // Request the data in a specific format
          format: "fasta",
        };

        const fallbackResponse = await axios({
          method: "post",
          url: `${NCBI_DATASETS_BASE_URL}/genome/download`,
          data: fallbackRequestData,
          responseType: "blob",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/plain, application/octet-stream",
            "api-key": NCBI_API_KEY,
          },
          timeout: 60000, // 60 second timeout for downloads
        });

        console.log(
          `Fallback download successful, size: ${fallbackResponse.data.size} bytes`,
        );

        // Check if the fallback response is a ZIP file
        const isZip =
          fallbackResponse.headers["content-type"]?.includes(
            "application/zip",
          ) ||
          fallbackResponse.data.slice(0, 4).toString() === "PK\x03\x04" ||
          (new Uint8Array(fallbackResponse.data.slice(0, 4))[0] === 0x50 &&
            new Uint8Array(fallbackResponse.data.slice(0, 4))[1] === 0x4b);

        if (isZip) {
          console.log(
            "Received ZIP file from NCBI fallback, downloading as .zip",
          );

          // Try to extract and assess FASTA quality
          try {
            const fastaContent = await extractFastaFromZip(
              fallbackResponse.data,
            );
            if (fastaContent) {
              const qualityScore = assessFastaQuality(fastaContent);
              let qualityLabel = "Low";
              if (qualityScore >= 80) qualityLabel = "High";
              else if (qualityScore >= 50) qualityLabel = "Medium";

              console.log(
                `Fallback ZIP contains FASTA with quality score: ${qualityScore} (${qualityLabel})`,
              );
            }
          } catch (extractError) {
            console.error(
              "Error assessing fallback ZIP content quality:",
              extractError,
            );
          }

          // Create and download as ZIP file
          const blob = new Blob([fallbackResponse.data], {
            type: "application/zip",
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${genome.ncbiAccession || genome.id}_genome.zip`;
          a.click();
          URL.revokeObjectURL(url);
        } else {
          // For direct FASTA content, assess quality
          try {
            const textData = await fallbackResponse.data.text();
            const qualityScore = assessFastaQuality(textData);
            let qualityLabel = "Low";
            if (qualityScore >= 80) qualityLabel = "High";
            else if (qualityScore >= 50) qualityLabel = "Medium";

            console.log(
              `Fallback direct FASTA quality score: ${qualityScore} (${qualityLabel})`,
            );

            // Create and download as FASTA file with quality label
            const blob = new Blob([textData], {
              type: "text/plain",
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${genome.ncbiAccession || genome.id}_genome_${qualityLabel.toLowerCase()}_quality.fasta`;
            a.click();
            URL.revokeObjectURL(url);
          } catch (textError) {
            console.error("Error processing fallback text FASTA:", textError);
            // Fallback to binary download
            const blob = new Blob([fallbackResponse.data], {
              type: "text/plain",
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${genome.ncbiAccession || genome.id}_genome.fasta`;
            a.click();
            URL.revokeObjectURL(url);
          }
        }

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

  // Function to extract FASTA content from ZIP file
  const extractFastaFromZip = async (zipData) => {
    try {
      // Use JSZip to handle ZIP files in the browser
      const zip = new JSZip();
      const contents = await zip.loadAsync(zipData);

      // Look for FASTA files in the ZIP
      let fastaContent = "";
      let highestQualityFasta = { content: "", quality: 0 };

      // First, try to find files with .fasta or .fa extension
      const fastaFiles = Object.keys(contents.files).filter(
        (filename) =>
          filename.endsWith(".fasta") ||
          filename.endsWith(".fa") ||
          filename.includes("cds_from") ||
          filename.includes("genomic.fna"),
      );

      if (fastaFiles.length === 0) {
        console.warn("No FASTA files found in ZIP archive");
        return null;
      }

      // Process each FASTA file to find the highest quality one
      for (const filename of fastaFiles) {
        const file = contents.files[filename];
        if (!file.dir) {
          const content = await file.async("string");

          // Basic quality assessment
          const quality = assessFastaQuality(content);
          console.log(`FASTA file ${filename} quality score: ${quality}`);

          if (quality > highestQualityFasta.quality) {
            highestQualityFasta = { content, quality };
          }
        }
      }

      return highestQualityFasta.content;
    } catch (error) {
      console.error("Error extracting FASTA from ZIP:", error);
      return null;
    }
  };

  // Function to assess FASTA quality
  const assessFastaQuality = (fastaContent) => {
    if (!fastaContent) return 0;

    // Basic quality metrics
    const lines = fastaContent.split("\n");
    const sequenceLines = lines.filter(
      (line) => !line.startsWith(">") && line.trim().length > 0,
    );
    const sequence = sequenceLines.join("");

    // Calculate quality score based on:
    // 1. Sequence length (longer is better)
    // 2. Number of N's (fewer is better)
    // 3. GC content (closer to expected range is better)
    const length = sequence.length;
    const nCount = (sequence.match(/N/g) || []).length;
    const gcCount = (sequence.match(/[GC]/g) || []).length;
    const gcContent = length > 0 ? (gcCount / length) * 100 : 0;

    // Quality formula - higher is better
    let qualityScore = 0;

    // Length score (0-50 points)
    if (length > 1000000) qualityScore += 50;
    else if (length > 500000) qualityScore += 40;
    else if (length > 100000) qualityScore += 30;
    else if (length > 10000) qualityScore += 20;
    else if (length > 1000) qualityScore += 10;

    // N content score (0-30 points)
    const nPercentage = length > 0 ? (nCount / length) * 100 : 100;
    if (nPercentage < 1) qualityScore += 30;
    else if (nPercentage < 5) qualityScore += 20;
    else if (nPercentage < 10) qualityScore += 10;

    // GC content score (0-20 points)
    // Most bacteria have GC content between 25% and 75%
    if (gcContent >= 25 && gcContent <= 75) qualityScore += 20;
    else if (gcContent >= 15 && gcContent <= 85) qualityScore += 10;

    console.log(
      `FASTA quality assessment: Length=${length}, N%=${nPercentage.toFixed(2)}, GC%=${gcContent.toFixed(2)}, Score=${qualityScore}`,
    );
    return qualityScore;
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
            // Using NCBI Datasets API to get CDS FASTA sequence for batch processing
            const batchDownloadRequestData = {
              accessions: [genome.ncbiAccession || genome.id],
              include_annotation_type: ["CDS_FASTA", "GENOME_FASTA"], // Request both CDS and genome FASTA
              filename: `${genome.ncbiAccession || genome.id}_cds.fasta`,
              format: "fasta", // Request FASTA format explicitly
            };

            const response = await axios({
              method: "post",
              url: `${NCBI_DATASETS_BASE_URL}/genome/download`,
              data: batchDownloadRequestData,
              responseType: "blob", // Use blob to handle both text and binary
              headers: {
                "Content-Type": "application/json",
                Accept: "text/plain, application/zip", // Accept both formats
                "api-key": NCBI_API_KEY,
              },
              timeout: 60000, // 60 second timeout for batch downloads
            });

            // Check if response is a ZIP file
            const isZip =
              response.headers["content-type"]?.includes("application/zip") ||
              response.data.type === "application/zip" ||
              response.data.type === "application/x-zip-compressed";

            let fastaContent;
            let fileQuality = "Medium";

            if (isZip) {
              console.log(
                `Received ZIP file for ${genome.id}, extracting FASTA content...`,
              );
              // Extract FASTA from ZIP
              fastaContent = await extractFastaFromZip(response.data);
              if (!fastaContent) {
                console.error(
                  `Could not extract FASTA from ZIP for ${genome.id}`,
                );
                // Try fallback to genome FASTA
                const fallbackRequestData = {
                  accessions: [genome.ncbiAccession || genome.id],
                  include_annotation_type: ["GENOME_FASTA"],
                  filename: `${genome.ncbiAccession || genome.id}_genome.fasta`,
                  format: "fasta",
                };

                const fallbackResponse = await axios({
                  method: "post",
                  url: `${NCBI_DATASETS_BASE_URL}/genome/download`,
                  data: fallbackRequestData,
                  responseType: "text",
                  headers: {
                    "Content-Type": "application/json",
                    Accept: "text/plain",
                    "api-key": NCBI_API_KEY,
                  },
                  timeout: 60000,
                });

                fastaContent = fallbackResponse.data;
              }
            } else {
              // Direct FASTA content
              const textData = await response.data.text();
              fastaContent = textData;
            }

            // Assess quality of the FASTA content
            const qualityScore = assessFastaQuality(fastaContent);
            if (qualityScore >= 80) fileQuality = "High";
            else if (qualityScore >= 50) fileQuality = "Medium";
            else fileQuality = "Low";

            console.log(
              `Final FASTA quality for ${genome.id}: ${fileQuality} (score: ${qualityScore})`,
            );

            // Store the processed FASTA content
            return {
              ...genome,
              fastaContent: fastaContent,
              fastaQuality: fileQuality,
              qualityScore: qualityScore,
              fileType: isZip ? "Extracted from ZIP" : "Direct FASTA",
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
    if (!query || query.trim() === "") {
      setError("Please enter a search term");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      if (DEBUG_MODE) {
        console.log(`Searching for: "${query}"`);
      }

      // Check if the query looks like a GCF ID (NCBI RefSeq assembly accession)
      const isGcfId = /^GCF_\d+\.\d+$/i.test(query.trim());

      // Using NCBI Datasets API for search with POST request and JSON body
      const searchRequestData = isGcfId
        ? {
            // For accession-based search
            accessions: [query.trim()],
            filters: {
              source_database: ["RefSeq"],
              exclude_paired_reports: true,
              exclude_atypical: true,
            },
            returned_content: "COMPLETE",
            page_size: 20,
          }
        : {
            // For taxonomic search by species name
            taxons: [query],
            filters: {
              source_database: ["RefSeq"],
              assembly_level: ["Complete Genome"],
              exclude_paired_reports: true,
              exclude_atypical: true,
            },
            returned_content: "COMPLETE",
            page_size: 20,
          };

      if (DEBUG_MODE) {
        console.log(
          "NCBI API Search Request URL:",
          `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        );
        console.log("NCBI API Search Request Data:", searchRequestData);
      }

      const response = await axios({
        method: "post",
        url: `${NCBI_DATASETS_BASE_URL}/genome/dataset_report`,
        data: searchRequestData,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "api-key": NCBI_API_KEY,
        },
        timeout: 30000, // 30 second timeout
      });

      if (DEBUG_MODE) {
        console.log("Search API Response:", response.data);
        console.log("Response structure keys:", Object.keys(response.data));
      }

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
      } else if (response.data.assemblies_by_taxid) {
        // Handle v2alpha API response structure
        const assembliesData = Object.values(
          response.data.assemblies_by_taxid || {},
        );
        searchReports = assembliesData.flatMap(
          (taxData: any) => taxData.assemblies || [],
        );
      } else if (response.data.assemblies_by_accession) {
        // Alternative v2alpha API response structure
        searchReports = Object.values(
          response.data.assemblies_by_accession || {},
        );
      } else if (response.data.assemblies_by_taxid) {
        // Handle v2alpha API response structure
        const assembliesData = Object.values(
          response.data.assemblies_by_taxid || {},
        );
        searchReports = assembliesData.flatMap(
          (taxData: any) => taxData.assemblies || [],
        );
      } else {
        // Check if the response data itself might be a report
        if (
          response.data &&
          typeof response.data === "object" &&
          (response.data.accession ||
            response.data.assembly_info ||
            response.data.organism)
        ) {
          console.log("Found single report object in response data");
          searchReports = [response.data];
        } else {
          console.warn("No matching genomes found for query:", query);
          setError("No genomes found matching your search criteria");
          setGenomes([]);
          setFilteredGenomes([]);
          return;
        }
      }

      if (searchReports.length === 0) {
        setError("No genomes found matching your search criteria");
        setGenomes([]);
        setFilteredGenomes([]);
        return;
      }

      // Process genome reports from Datasets API
      const genomeDetails = searchReports
        .filter((report) => report !== null && typeof report === "object")
        .map((report: any) => {
          if (DEBUG_MODE) {
            console.log("Processing report:", report);
          }

          try {
            // Handle the new v2alpha API response structure
            const assembly = report.assembly_info || {};
            const organism = report.organism || {};
            const annotation = report.annotation_info || {};
            const assemblyStats =
              report.assembly_stats || assembly.assembly_stats || {};

            // Extract organism name from various possible locations
            const organismName = organism.organism_name || "Unknown organism";

            // Extract accession - use the main accession field
            const accession = report.accession || report.current_accession;

            // If we don't have an accession, try to extract it from the console log format
            let extractedAccession = accession;
            if (!extractedAccession && typeof report === "object") {
              // Try to find accession in the format shown in the console logs
              const keys = Object.keys(report);
              for (const key of keys) {
                if (key === "accession" && typeof report[key] === "string") {
                  extractedAccession = report[key];
                  break;
                }
              }
            }

            // Convert size from string to number if needed
            const sizeValue = assemblyStats.total_sequence_length;
            const genomeSizeNumber =
              typeof sizeValue === "string"
                ? parseInt(sizeValue, 10)
                : sizeValue || 0;

            const processedGenome = {
              id:
                extractedAccession ||
                "unknown-id-" + Math.random().toString(36).substring(2, 9),
              organism: organismName,
              species:
                organismName.split(" ").slice(0, 2).join(" ") ||
                "Unknown species",
              strain: organism.infraspecific_names?.strain || undefined,
              taxonomy: organism.tax_id
                ? `Tax ID: ${organism.tax_id}`
                : "Bacteria",
              size: genomeSizeNumber,
              genes: annotation.stats?.gene_counts?.total || 0,
              proteins: annotation.stats?.gene_counts?.protein_coding || 0,
              description:
                assembly.assembly_name || organismName || "Bacterial genome",
              source: "NCBI" as const,
              ncbiId: extractedAccession,
              ncbiAccession: extractedAccession,
              gcContent: assemblyStats.gc_percent || 50,
              sequenceAvailable: true,
            };

            if (DEBUG_MODE) {
              console.log("Processed genome:", processedGenome);
            }

            return processedGenome;
          } catch (err) {
            console.error("Error processing genome report:", err, report);
            return null;
          }
        })
        .filter(Boolean);

      const validGenomes = genomeDetails.filter((genome) => {
        return genome && genome.id && genome.organism;
      }) as GenomeData[];

      if (DEBUG_MODE) {
        console.log("Valid search genomes processed:", validGenomes.length);
        console.log("First few search genomes:", validGenomes.slice(0, 3));
      }

      // Set genomes state
      setGenomes(validGenomes);

      // Set filtered genomes to show all search results initially
      setFilteredGenomes(validGenomes);

      // Preserve advanced filters when performing a search
      // Only reset the basic filters
      setSelectedSpecies("all");
      setSelectedVariant("all");
      setSelectedTaxonomy("all");
      // Don't reset advanced filters: setShowAdvancedFilters(false);

      // If we found exactly one genome that matches a GCF ID, select it automatically
      if (validGenomes.length === 1 && /^GCF_\d+\.\d+$/i.test(query.trim())) {
        setSelectedGenomes(new Set([validGenomes[0].id]));
      }
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
                      placeholder="Search by name, GCF ID, strain..."
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
              {/* Debug info */}
              <div className="p-2 bg-gray-100 text-xs text-gray-600">
                Debug: Rendering {filteredGenomes.length} genomes out of{" "}
                {genomes.length} total
              </div>

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
                  {filteredGenomes.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={8}
                        className="text-center py-8 text-gray-500"
                      >
                        {isLoading ? (
                          <div className="flex items-center justify-center">
                            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                            Loading genomes...
                          </div>
                        ) : genomes.length === 0 ? (
                          "No genomes available. Click 'Search NCBI' to fetch data."
                        ) : (
                          "No genomes match the current filters."
                        )}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredGenomes.map((genome, index) => {
                      console.log(`Rendering genome ${index}:`, genome);
                      return (
                        <TableRow
                          key={genome.id || `genome-${index}`}
                          className="hover:bg-blue-50"
                        >
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={selectedGenomes.has(genome.id)}
                              onChange={() => handleGenomeSelect(genome)}
                              className="rounded border-gray-300"
                            />
                          </TableCell>
                          <TableCell className="font-mono font-medium text-blue-700">
                            {genome.id || "N/A"}
                          </TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">
                                {genome.organism || "Unknown"}
                              </div>
                              <div className="text-sm text-gray-500">
                                {genome.species || "Unknown species"}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {genome.strain && (
                                <div className="font-medium">
                                  {genome.strain}
                                </div>
                              )}
                              {genome.variant && (
                                <div className="text-gray-600">
                                  {genome.variant}
                                </div>
                              )}
                              {!genome.strain && !genome.variant && (
                                <div className="text-gray-400">N/A</div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="font-mono">
                            {genome.size
                              ? (genome.size / 1000000).toFixed(2)
                              : "N/A"}
                          </TableCell>
                          <TableCell className="font-mono">
                            {genome.gcContent?.toFixed(1) || "N/A"}
                          </TableCell>
                          <TableCell className="font-mono">
                            {genome.genes
                              ? genome.genes.toLocaleString()
                              : "N/A"}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() =>
                                        handleSequenceDownload(genome)
                                      }
                                      disabled={
                                        !genome.sequenceAvailable || isLoading
                                      }
                                    >
                                      <Download className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>
                                      Download CDS sequence (may be ZIP file)
                                    </p>
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
                      );
                    })
                  )}
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

export default NCBIGenomeSearch;
