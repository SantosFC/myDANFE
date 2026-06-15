import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Painel from "./pages/Painel";
import ImportarNota from "./pages/ImportarNota";
import Produtos from "./pages/Produtos";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <nav className="navbar">
        <span className="navbar-brand">myDANFE</span>
        <NavLink to="/" end>Painel</NavLink>
        <NavLink to="/importar">Importar Nota</NavLink>
        <NavLink to="/produtos">Produtos</NavLink>
      </nav>
      <main className="container">
        <Routes>
          <Route path="/" element={<Painel />} />
          <Route path="/importar" element={<ImportarNota />} />
          <Route path="/produtos" element={<Produtos />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
