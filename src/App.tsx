"use client";
import { Suspense } from "react";
import { useRoutes, Routes, Route } from "react-router-dom";
import Home from "./components/home";
import { Header } from "./components/Header";
import { HeroSection } from "./components/blocks/hero-section-5";
import routes from "tempo-routes";

function App() {
  const tempoElements = useRoutes(routes);

  return (
    <div className="relative min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#020617] to-slate-950 text-slate-50 overflow-hidden">
      {/* Aesthetic Background Glows */}
      <div className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vh] rounded-full bg-cyan-600/40 blur-[120px] pointer-events-none z-0" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[50vw] h-[50vh] rounded-full bg-amber-500/30 blur-[120px] pointer-events-none z-0" />

      <div className="relative z-10">
        <Suspense fallback={<p>Loading...</p>}>
          <>
            <Header />
            <Routes>
              <Route path="/" element={<HeroSection />} />
              <Route path="/app" element={<Home />} />
            </Routes>
            {import.meta.env.VITE_TEMPO === "true" && tempoElements}
          </>
        </Suspense>
      </div>
    </div>
  );
}

export default App;
