import { Suspense } from "react";
import { useRoutes, Routes, Route, BrowserRouter } from "react-router-dom";
import Home from "./components/home";
import routes from "tempo-routes";

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<p>Loading...</p>}>
        <>
          <Routes>
            <Route path="/" element={<Home />} />
          </Routes>
          {useRoutes(routes)}
        </>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
