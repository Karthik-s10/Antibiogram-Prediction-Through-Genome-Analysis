"use client";
import { Suspense } from "react";
import { useRoutes, Routes, Route } from "react-router-dom";
import Home from "./components/home";
import routes from "tempo-routes";

function App() {
  const tempoElements = useRoutes(routes);

  return (
    <div className="min-h-screen bg-background">
      <Suspense
        fallback={
          <div className="min-h-screen bg-background flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-xl revolut-gradient-blue animate-pulse" />
              <p className="text-muted-foreground">Loading...</p>
            </div>
          </div>
        }
      >
        <>
          <Routes>
            <Route path="/" element={<Home />} />
          </Routes>
          {import.meta.env.VITE_TEMPO === "true" && tempoElements}
        </>
      </Suspense>
    </div>
  );
}

export default App;
