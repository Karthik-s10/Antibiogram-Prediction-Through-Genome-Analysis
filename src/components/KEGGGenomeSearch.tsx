import React, { useState, useEffect } from "react";
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

interface KEGGGenome {
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
  keggUrl: string;
  ncbiId?: string;
  gcContent?: number;
  sequenceAvailable: boolean;
}

interface KEGGGenomeSearchProps {
  onGenomeSelect?: (genome: KEGGGenome) => void;
  onSequenceDownload?: (genome: KEGGGenome) => void;
  onBatchProcess?: (genomes: KEGGGenome[]) => void;
  className?: string;
}

const KEGGGenomeSearch = ({
  onGenomeSelect = () => {},
  onSequenceDownload = () => {},
  onBatchProcess = () => {},
  className = "",
}: KEGGGenomeSearchProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpecies, setSelectedSpecies] = useState("all");
  const [selectedVariant, setSelectedVariant] = useState("all");
  const [selectedTaxonomy, setSelectedTaxonomy] = useState("all");
  const [genomes, setGenomes] = useState<KEGGGenome[]>([]);
  const [filteredGenomes, setFilteredGenomes] = useState<KEGGGenome[]>([]);
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

  // Fetch real KEGG genome data
  const fetchKeggGenomes = async () => {
    setIsLoading(true);
    setError("");

    try {
      // In a real implementation, this would be a server endpoint that proxies to KEGG API
      // For now, we'll simulate a fetch with a delay
      const response = await fetch("/api/kegg/genomes");

      if (!response.ok) {
        throw new Error(`Failed to fetch KEGG genomes: ${response.status}`);
      }

      const data = await response.json();
      setGenomes(data);
      setFilteredGenomes(data);

      // Set filter ranges based on actual data
      const sizes = data.map((g: KEGGGenome) => g.size / 1000000); // Convert to Mbp
      const genes = data.map((g: KEGGGenome) => g.genes);
      const gcContents = data
        .map((g: KEGGGenome) => g.gcContent)
        .filter(Boolean);

      setSizeRange([Math.min(...sizes), Math.max(...sizes)]);
      setGeneCountRange([Math.min(...genes), Math.max(...genes)]);
      setGcContentRange([Math.min(...gcContents), Math.max(...gcContents)]);
    } catch (err) {
      console.error("Error fetching KEGG genomes:", err);
      setError(
        "Failed to fetch genome data from KEGG API. Using cached data instead.",
      );

      // Fallback to cached data
      const cachedGenomes = localStorage.getItem("keggGenomes");
      if (cachedGenomes) {
        const parsed = JSON.parse(cachedGenomes);
        setGenomes(parsed);
        setFilteredGenomes(parsed);
      } else {
        // If no cached data, use the sample data
        const sampleGenomes = getSampleGenomes();
        setGenomes(sampleGenomes);
        setFilteredGenomes(sampleGenomes);

        // Cache the sample data
        localStorage.setItem("keggGenomes", JSON.stringify(sampleGenomes));
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Sample genomes for fallback
  const getSampleGenomes = (): KEGGGenome[] => [
    {
      id: "kpn",
      organism: "Klebsiella pneumoniae",
      species: "K. pneumoniae",
      strain: "subsp. pneumoniae",
      variant: "MGH 78578",
      taxonomy:
        "Bacteria; Proteobacteria; Gammaproteobacteria; Enterobacterales",
      size: 5374361,
      genes: 5126,
      proteins: 4960,
      description: "Gram-negative, encapsulated, non-motile bacterium",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=kpn",
      ncbiId: "272620",
      gcContent: 57.2,
      sequenceAvailable: true,
    },
    {
      id: "eco",
      organism: "Escherichia coli",
      species: "E. coli",
      strain: "K-12",
      variant: "MG1655",
      taxonomy:
        "Bacteria; Proteobacteria; Gammaproteobacteria; Enterobacterales",
      size: 4641652,
      genes: 4321,
      proteins: 4285,
      description:
        "Model organism for bacterial genetics and molecular biology",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=eco",
      ncbiId: "511145",
      gcContent: 50.8,
      sequenceAvailable: true,
    },
    {
      id: "pae",
      organism: "Pseudomonas aeruginosa",
      species: "P. aeruginosa",
      strain: "PAO1",
      taxonomy:
        "Bacteria; Proteobacteria; Gammaproteobacteria; Pseudomonadales",
      size: 6264404,
      genes: 5570,
      proteins: 5563,
      description:
        "Opportunistic pathogen with intrinsic antibiotic resistance",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=pae",
      ncbiId: "208964",
      gcContent: 66.6,
      sequenceAvailable: true,
    },
    {
      id: "sau",
      organism: "Staphylococcus aureus",
      species: "S. aureus",
      strain: "subsp. aureus",
      variant: "N315",
      taxonomy: "Bacteria; Firmicutes; Bacilli; Bacillales",
      size: 2814816,
      genes: 2697,
      proteins: 2593,
      description:
        "Gram-positive pathogen, MRSA strains are multidrug-resistant",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=sau",
      ncbiId: "158878",
      gcContent: 32.8,
      sequenceAvailable: true,
    },
    {
      id: "efa",
      organism: "Enterococcus faecalis",
      species: "E. faecalis",
      strain: "V583",
      taxonomy: "Bacteria; Firmicutes; Bacilli; Lactobacillales",
      size: 3218031,
      genes: 3113,
      proteins: 3264,
      description: "Vancomycin-resistant enterococcus (VRE) reference strain",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=efa",
      ncbiId: "226185",
      gcContent: 37.4,
      sequenceAvailable: true,
    },
    {
      id: "aba",
      organism: "Acinetobacter baumannii",
      species: "A. baumannii",
      strain: "ATCC 17978",
      taxonomy:
        "Bacteria; Proteobacteria; Gammaproteobacteria; Pseudomonadales",
      size: 3976747,
      genes: 3830,
      proteins: 3785,
      description: "Multidrug-resistant nosocomial pathogen",
      keggUrl: "https://www.kegg.jp/kegg-bin/show_organism?org=aba",
      ncbiId: "400667",
      gcContent: 39.0,
      sequenceAvailable: true,
    },
  ];

  useEffect(() => {
    fetchKeggGenomes();
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

  const handleGenomeSelect = (genome: KEGGGenome) => {
    const newSelected = new Set(selectedGenomes);
    if (newSelected.has(genome.id)) {
      newSelected.delete(genome.id);
    } else {
      newSelected.add(genome.id);
    }
    setSelectedGenomes(newSelected);
    onGenomeSelect(genome);
  };

  const handleSequenceDownload = async (genome: KEGGGenome) => {
    setIsLoading(true);
    try {
      // Fetch sequence from KEGG API
      const response = await fetch(`/api/kegg/sequence/${genome.id}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch sequence: ${response.status}`);
      }

      const fastaContent = await response.text();

      // Create and download file
      const blob = new Blob([fastaContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${genome.id}_${genome.organism.replace(/\s+/g, "_")}.fasta`;
      a.click();
      URL.revokeObjectURL(url);

      onSequenceDownload(genome);
    } catch (error) {
      console.error("Error downloading sequence:", error);
      setError("Failed to download sequence. Using simulated data instead.");

      // Fallback to simulated sequence
      const mockSequence = generateMockSequence(genome.size);
      const fastaContent = `>${genome.id} ${genome.organism} ${genome.variant || genome.strain || ""} complete genome\n${mockSequence}`;

      // Create and download file
      const blob = new Blob([fastaContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${genome.id}_${genome.organism.replace(/\s+/g, "_")}.fasta`;
      a.click();
      URL.revokeObjectURL(url);

      onSequenceDownload(genome);
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

      // Call the batch processing function
      onBatchProcess(genomesToProcess);

      // In a real implementation, this would send the genomes to a backend for processing
      // and potentially redirect to a results page or show a notification
      await new Promise((resolve) => setTimeout(resolve, 2000)); // Simulate processing time

      // Success message would be handled by the parent component
    } catch (error) {
      console.error("Batch processing error:", error);
      setError("Failed to process genomes in batch mode");
    } finally {
      setIsBatchProcessing(false);
    }
  };

  const generateMockSequence = (length: number): string => {
    const bases = ["A", "T", "C", "G"];
    let sequence = "";
    for (let i = 0; i < Math.min(length, 1000); i++) {
      // Limit to 1000 bp for demo
      sequence += bases[Math.floor(Math.random() * 4)];
      if ((i + 1) % 80 === 0) sequence += "\n"; // Line breaks every 80 bases
    }
    return sequence;
  };

  const getUniqueValues = (key: keyof KEGGGenome) => {
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
              KEGG Genome Database
            </CardTitle>
            <CardDescription className="text-blue-700">
              Search and access bacterial genomes from the KEGG database for
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
                      window.open("https://www.kegg.jp/kegg/genome/", "_blank")
                    }
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Visit KEGG Genome Database</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent>
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
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearFilters}
                  className="flex items-center"
                >
                  <Filter className="mr-2 h-4 w-4" />
                  Clear Filters
                </Button>
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
                                <p>Download FASTA sequence</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() =>
                                    window.open(genome.keggUrl, "_blank")
                                  }
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>View in KEGG database</p>
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
                              Download
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                window.open(genome.keggUrl, "_blank")
                              }
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

export default KEGGGenomeSearch;
