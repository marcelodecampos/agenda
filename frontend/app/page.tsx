"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useAuth } from "./auth-provider";

type Oferta = {
  servico: {
    id: string;
    nome: string;
    categoria: string;
    duracao_base_minutos: number;
    preco_base: string;
  };
  organizacao: { nome: string } | null;
  distancia_km: string | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

function formatPrice(value: string) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDistance(value: string | null) {
  if (!value) return null;
  return `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km`;
}

export default function Home() {
  const {
    authenticated,
    loading: authLoading,
    userName,
    roles,
    login,
    logout,
  } = useAuth();
  const [categoria, setCategoria] = useState("");
  const [endereco, setEndereco] = useState("");
  const [raioKm, setRaioKm] = useState("10");
  const [ofertas, setOfertas] = useState<Oferta[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [pesquisou, setPesquisou] = useState(false);

  async function buscarOfertas(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCarregando(true);
    setErro("");
    setPesquisou(true);

    const parametros = new URLSearchParams();
    if (categoria.trim()) parametros.set("termo", categoria.trim());
    if (endereco.trim()) {
      parametros.set("endereco", endereco.trim());
      if (raioKm) parametros.set("raio_km", raioKm);
    }

    try {
      const resposta = await fetch(`${apiUrl}/descoberta?${parametros}`);
      if (!resposta.ok) throw new Error("Não foi possível carregar as ofertas.");
      setOfertas((await resposta.json()) as Oferta[]);
    } catch {
      setOfertas([]);
      setErro("Não foi possível buscar agora. Verifique se a API está em execução.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <Link className="brand" href="/">agenda<span>.</span></Link>
        <div className="account-actions">
          <a className="provider-link" href="#ofertas">Sou profissional?</a>
          {!authLoading && (authenticated ? (
            <button className="account-button" type="button" onClick={() => void logout()}>
              {userName} · Sair
            </button>
          ) : (
            <button className="account-button" type="button" onClick={() => void login()}>
              Entrar
            </button>
          ))}
        </div>
      </header>

      {authenticated && (
          <section className="account-panel" aria-label="Área do usuário">
          <div>
            <p className="eyebrow">Área autenticada</p>
            <h2>Olá, {userName}</h2>
            <p className="account-summary">
              &quot;Encontre serviços e ofertas perto de você&quot;
            </p>
            {roles.includes("platform_admin") && (
              <Link className="admin-entry-link" href="/admin">
                Administração
              </Link>
            )}
          </div>
        </section>
      )}

      <>
        <section className="hero">
          <p className="eyebrow">Cuide de você, no seu tempo</p>
          <h1>Encontre o cuidado que cabe na sua rotina.</h1>
          <p className="hero-copy">Descubra profissionais e serviços de beleza, saúde e bem-estar perto de você.</p>

          <form className="search-panel" onSubmit={buscarOfertas}>
            <label>
              <span>O que você procura?</span>
              <input value={categoria} onChange={(event) => setCategoria(event.target.value)} placeholder="Ex.: manicure, massagem" />
            </label>
            <label>
              <span>Onde?</span>
              <input value={endereco} onChange={(event) => setEndereco(event.target.value)} placeholder="Endereço ou bairro" />
            </label>
            <label className="radius-field">
              <span>Raio</span>
              <select value={raioKm} onChange={(event) => setRaioKm(event.target.value)}>
                <option value="5">5 km</option>
                <option value="10">10 km</option>
                <option value="25">25 km</option>
                <option value="50">50 km</option>
              </select>
            </label>
            <button type="submit" disabled={carregando}>{carregando ? "Buscando..." : "Buscar ofertas"}</button>
          </form>
        </section>

        <section className="results" id="ofertas" aria-live="polite">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Para o seu próximo momento</p>
              <h2>{pesquisou ? "Ofertas encontradas" : "Comece sua busca"}</h2>
            </div>
            {pesquisou && <span className="result-count">{ofertas.length} resultado{ofertas.length === 1 ? "" : "s"}</span>}
          </div>

          {erro && <p className="message error">{erro}</p>}
          {!erro && pesquisou && ofertas.length === 0 && !carregando && <p className="message">Nenhuma oferta encontrada. Tente uma categoria ou local diferente.</p>}
          {!pesquisou && <p className="message intro-message">Busque por um serviço para ver opções disponíveis.</p>}

          <div className="offer-grid">
            {ofertas.map((oferta) => (
              <article className="offer-card" key={oferta.servico.id}>
                <div className="offer-mark">{oferta.servico.nome.slice(0, 1).toUpperCase()}</div>
                <div className="offer-content">
                  <p className="card-category">{oferta.servico.categoria}</p>
                  <h3>{oferta.servico.nome}</h3>
                  <p className="provider-name">{oferta.organizacao?.nome ?? "Profissional independente"}</p>
                  <div className="offer-details">
                    <strong>{formatPrice(oferta.servico.preco_base)}</strong>
                    <span>{oferta.servico.duracao_base_minutos} min</span>
                    {formatDistance(oferta.distancia_km) && <span>{formatDistance(oferta.distancia_km)}</span>}
                  </div>
                </div>
                <button className="details-button" type="button" aria-label={`Ver detalhes de ${oferta.servico.nome}`}>Ver detalhes</button>
              </article>
            ))}
          </div>
        </section>
      </>
    </main>
  );
}
