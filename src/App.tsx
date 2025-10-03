import { Suspense } from "react";
import Home from "./components/home";

function App() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <Home />
    </Suspense>
  );
}

export default App;
