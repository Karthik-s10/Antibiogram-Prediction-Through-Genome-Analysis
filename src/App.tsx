"use client";
import { Suspense } from "react";
import { useRoutes, Routes, Route } from "react-router-dom";
import { WavyBackground } from "./components/ui/wavy-background";
import Home from "./components/home";
import routes from "tempo-routes";

function App() {
  const tempoElements = useRoutes(routes);

  return (
    <div className="relative min-h-screen">
      <WavyBackground
        colors={["#10b981", "#14b8a6", "#0ea5e9", "#8b5cf6", "#ec4899"]}
        waveWidth={50}
        backgroundFill="rgb(236 253 245)"
        blur={3}
        speed="fast"
        waveOpacity={0.6}
      />
      <div className="relative z-10">
        <Suspense fallback={<p>Loading...</p>}>
          <>
            <Routes>
              <Route path="/" element={<Home />} />
            </Routes>
            {import.meta.env.VITE_TEMPO === "true" && tempoElements}
          </>
        </Suspense>
      </div>
    </div>
  );
}

export default App;
