"use client";
import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface WavyBackgroundProps {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  colors?: string[];
  waveWidth?: number;
  backgroundFill?: string;
  blur?: number;
  speed?: "slow" | "fast";
  waveOpacity?: number;
}

export const WavyBackground = ({
  children,
  className,
  containerClassName,
  colors = ["#10b981", "#14b8a6", "#0ea5e9", "#8b5cf6", "#ec4899"],
  waveWidth = 50,
  backgroundFill = "rgb(236 253 245)",
  blur = 3,
  speed = "fast",
  waveOpacity = 0.6,
}: WavyBackgroundProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameId = useRef<number | null>(null);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w: number;
    let h: number;

    const setCanvasSize = () => {
      w = canvas.offsetWidth;
      h = canvas.offsetHeight;
      canvas.width = w * window.devicePixelRatio;
      canvas.height = h * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    setCanvasSize();
    window.addEventListener("resize", setCanvasSize);

    // DNA base pair colors (A, T, G, C)
    const baseColors = colors.length >= 4 ? colors : [
      "#10b981", // Emerald (A)
      "#14b8a6", // Teal (T)
      "#0ea5e9", // Blue (G)
      "#8b5cf6", // Purple (C)
      "#ec4899"  // Pink (extra)
    ];

    const drawDNAStrand = (
      centerX: number,
      amplitude: number,
      frequency: number,
      phase: number,
      strandColor: string,
      basePairSpacing: number = 15
    ) => {
      const strand1Y: number[] = [];
      const strand2Y: number[] = [];
      const basePairWidth = 8;

      // Calculate strand positions
      for (let x = 0; x < w; x++) {
        const wave1 = amplitude * Math.sin((x / frequency) + phase);
        const wave2 = amplitude * Math.sin((x / frequency) + phase + Math.PI);
        strand1Y.push(h / 2 + wave1);
        strand2Y.push(h / 2 + wave2);
      }

      // Draw first strand (backbone)
      ctx.beginPath();
      ctx.moveTo(0, strand1Y[0]);
      for (let x = 1; x < w; x++) {
        ctx.lineTo(x, strand1Y[x]);
      }
      ctx.strokeStyle = strandColor;
      ctx.lineWidth = 3;
      ctx.globalAlpha = waveOpacity;
      ctx.stroke();

      // Draw second strand (backbone)
      ctx.beginPath();
      ctx.moveTo(0, strand2Y[0]);
      for (let x = 1; x < w; x++) {
        ctx.lineTo(x, strand2Y[x]);
      }
      ctx.strokeStyle = strandColor;
      ctx.lineWidth = 3;
      ctx.stroke();

      // Draw base pairs (rungs of the ladder)
      for (let x = 0; x < w; x += basePairSpacing) {
        const y1 = strand1Y[Math.floor(x)];
        const y2 = strand2Y[Math.floor(x)];
        
        // Alternate base pair colors
        const baseColor = baseColors[Math.floor((x / basePairSpacing) + phase * 10) % baseColors.length];
        
        // Draw base pair connection
        ctx.beginPath();
        ctx.moveTo(x, y1);
        ctx.lineTo(x, y2);
        ctx.strokeStyle = baseColor;
        ctx.lineWidth = 2;
        ctx.globalAlpha = waveOpacity * 0.8;
        ctx.stroke();

        // Draw small circles at base pair ends (nucleotides)
        ctx.beginPath();
        ctx.arc(x, y1, 2, 0, Math.PI * 2);
        ctx.fillStyle = baseColor;
        ctx.globalAlpha = waveOpacity;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x, y2, 2, 0, Math.PI * 2);
        ctx.fillStyle = baseColor;
        ctx.fill();
      }
    };

    const render = () => {
      // Create a more vibrant gradient background
      const gradient = ctx.createLinearGradient(0, 0, w, h);
      gradient.addColorStop(0, '#e0f2fe');  // Brighter light blue
      gradient.addColorStop(0.4, '#ede9fe'); // Brighter light purple
      gradient.addColorStop(0.7, '#fae8ff'); // Brighter light pink
      gradient.addColorStop(1, '#f0f9ff');   // Soft blue-white
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);
    };

    render();
    
    // Handle window resize
    const handleResize = () => {
      setCanvasSize();
      render();
    };
    
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener("resize", setCanvasSize);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [colors, waveWidth, backgroundFill, blur, speed, waveOpacity]);

  return (
    <div className={cn("fixed inset-0 z-0 w-full h-full overflow-hidden", containerClassName)}>
      <canvas
        className="absolute inset-0 w-full h-full"
        ref={canvasRef}
        style={{ filter: `blur(${blur}px)` }}
      />
      {children && (
        <div className={cn("relative z-10", className)}>{children}</div>
      )}
    </div>
  );
};

