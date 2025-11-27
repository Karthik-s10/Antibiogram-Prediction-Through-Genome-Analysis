import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Upload,
  FileWarning,
  CheckCircle,
  AlertCircle,
  Sparkles,
  Dna,
} from "lucide-react";

interface GenomeUploaderProps {
  onFileUpload?: (file: File) => void;
  isProcessing?: boolean;
  processingProgress?: number;
  error?: string;
}

const funFacts = [
  "🧬 The human genome contains about 3 billion base pairs!",
  "🦠 Bacteria can share genes horizontally, like trading cards!",
  "💊 Penicillin was discovered by accident in 1928!",
  "🔬 A single bacterium can multiply into millions in just hours!",
  "🌟 Some bacteria can survive in space for years!",
  "🧪 Antibiotic resistance genes can jump between different bacterial species!",
  "⚡ DNA sequencing used to take years, now it takes hours!",
  "🎯 Machine learning can predict antibiotic resistance with 95% accuracy!",
  "🌈 Bacteria come in amazing shapes: spheres, rods, and spirals!",
  "🔥 Some bacteria can survive temperatures over 100°C!",
  "💎 Your genome is 99.9% identical to every other human's!",
  "🚀 Genomic medicine is revolutionizing personalized healthcare!",
  "🎨 Each bacterial colony has its own unique genetic fingerprint!",
  "⭐ The first bacterial genome was sequenced in 1995!",
  "🌊 Ocean bacteria produce half of the world's oxygen!",
];

const GenomeUploader = ({
  onFileUpload = () => {},
  isProcessing = false,
  processingProgress = 0,
  error = "",
}: GenomeUploaderProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [validationMessage, setValidationMessage] = useState("");
  const [validationStatus, setValidationStatus] = useState<
    "success" | "error" | null
  >(null);
  const [currentFact, setCurrentFact] = useState("");
  const [factIndex, setFactIndex] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateFastaFile = (file: File): Promise<boolean> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        // Basic FASTA validation - check for '>' character at the beginning
        // and sequence content with valid nucleotides
        if (content && content.trim().startsWith(">")) {
          const lines = content.split("\n");
          const sequenceLines = lines.filter(
            (line) => !line.startsWith(">") && line.trim().length > 0,
          );
          const sequence = sequenceLines.join("").toUpperCase();

          // Check if sequence contains only valid nucleotides (A, C, G, T, N)
          const validNucleotides = /^[ACGTN]+$/;
          if (validNucleotides.test(sequence)) {
            setValidationStatus("success");
            setValidationMessage("Valid FASTA file detected");
            resolve(true);
          } else {
            setValidationStatus("error");
            setValidationMessage(
              "Invalid sequence content. FASTA should contain only A, C, G, T, N nucleotides.",
            );
            resolve(false);
          }
        } else {
          setValidationStatus("error");
          setValidationMessage(
            'Invalid FASTA format. File should start with ">" character.',
          );
          resolve(false);
        }
      };
      reader.readAsText(file);
    });
  };

  const handleFileDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];

      // Check file extension
      if (
        !droppedFile.name.endsWith(".fasta") &&
        !droppedFile.name.endsWith(".fa")
      ) {
        setValidationStatus("error");
        setValidationMessage(
          "Please upload a file with .fasta or .fa extension",
        );
        return;
      }

      setFile(droppedFile);
      const isValid = await validateFastaFile(droppedFile);

      if (isValid) {
        onFileUpload(droppedFile);
      }
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];

      // Check file extension
      if (
        !selectedFile.name.endsWith(".fasta") &&
        !selectedFile.name.endsWith(".fa")
      ) {
        setValidationStatus("error");
        setValidationMessage(
          "Please upload a file with .fasta or .fa extension",
        );
        return;
      }

      setFile(selectedFile);
      const isValid = await validateFastaFile(selectedFile);

      if (isValid) {
        onFileUpload(selectedFile);
      }
    }
  };

  const handleBrowseClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Fun facts rotation during processing
  useEffect(() => {
    if (isProcessing) {
      setCurrentFact(funFacts[0]);
      setFactIndex(0);

      const interval = setInterval(() => {
        setFactIndex((prevIndex) => {
          const nextIndex = (prevIndex + 1) % funFacts.length;
          setCurrentFact(funFacts[nextIndex]);
          return nextIndex;
        });
      }, 3000); // Change fact every 3 seconds

      return () => clearInterval(interval);
    }
  }, [isProcessing]);

  return (
    <Card className="w-full max-w-3xl mx-auto bg-card border shadow-lg">
      <CardContent className="p-6">
        <div className="text-center mb-6">
          <div className="flex items-center justify-center mb-3">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-emerald-600 via-teal-600 to-blue-600 bg-clip-text text-transparent">
              Upload Genome Sequence
            </h2>
          </div>
          <p className="text-gray-700 mt-2 text-lg">
            Upload a bacterial genome in FASTA format (.fasta or .fa) to predict
            its antibiogram with AI magic!
          </p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {validationStatus && (
          <Alert
            variant={validationStatus === "success" ? "default" : "destructive"}
            className="mb-6"
          >
            {validationStatus === "success" ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <FileWarning className="h-4 w-4" />
            )}
            <AlertTitle>
              {validationStatus === "success" ? "Success" : "Validation Error"}
            </AlertTitle>
            <AlertDescription>{validationMessage}</AlertDescription>
          </Alert>
        )}

        <div
          className={`border-3 border-dashed rounded-xl p-8 text-center transition-all duration-300 transform hover:scale-105 ${
            isDragging
              ? "border-primary bg-primary/10 shadow-lg"
              : "border-muted-foreground/30 hover:border-primary bg-muted/20 hover:shadow-md"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleFileDrop}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".fasta,.fa"
            onChange={handleFileSelect}
          />

          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="p-4 rounded-full bg-primary/20 animate-pulse">
              <Upload className="h-10 w-10 text-primary" />
            </div>
            <div>
              <p className="text-xl font-semibold text-foreground">
                Drag and drop your FASTA file here
              </p>
              <p className="text-sm text-muted-foreground mt-1 font-medium">or</p>
              <Button
                onClick={handleBrowseClick}
                className="mt-3 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-6 py-2 rounded-full shadow-lg transform hover:scale-105 transition-all duration-200"
                disabled={isProcessing}
              >
                Browse Files
              </Button>
            </div>
            <p className="text-sm text-muted-foreground font-medium">
              📁 Supported formats: .fasta, .fa (max 50MB)
            </p>
          </div>
        </div>

        {file && !isProcessing && validationStatus === "success" && (
          <div className="mt-4 p-4 bg-green-50 rounded-xl flex items-center border border-green-200 shadow-md">
            <CheckCircle className="h-6 w-6 text-green-600 mr-3 animate-bounce" />
            <span className="text-sm text-green-800 font-semibold">
              🎉 {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB) ready
              for AI analysis!
            </span>
          </div>
        )}

        {isProcessing && (
          <div className="mt-6 space-y-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center">
                <Sparkles className="h-5 w-5 text-primary mr-2 animate-spin" />
                <span className="text-lg font-semibold text-foreground">
                  🧬 AI is analyzing your genome...
                </span>
              </div>
              <span className="text-lg font-bold text-primary">
                {processingProgress}%
              </span>
            </div>
            <Progress
              value={processingProgress}
              className="h-3"
            />

            {/* Fun Facts Display */}
            <div className="bg-muted/50 p-4 rounded-xl border border-border shadow-md">
              <div className="flex items-center mb-2">
                <Sparkles className="h-5 w-5 text-primary mr-2" />
                <span className="font-bold text-foreground">
                  🎓 Did you know?
                </span>
              </div>
              <p className="text-sm text-muted-foreground font-medium animate-pulse">
                {currentFact}
              </p>
            </div>

            <p className="text-sm text-muted-foreground text-center font-medium">
              ⏱️ This may take a few minutes depending on the genome size
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default GenomeUploader;
