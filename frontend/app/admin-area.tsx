"use client";

import { FormEvent, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";
import { useAuth } from "./auth-provider";

type NomeServico = { id: string; nome: string };
type AdminAreaProps = { userName: string | null; logout: () => Promise<void> };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

export default function AdminArea({ userName, logout }: AdminAreaProps) {
  const { apiFetch } = useAuth();
  const [section, setSection] = useState<"overview" | "catalog">("overview");
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [buscaOpen, setBuscaOpen] = useState(false);
  const [exclusaoPendente, setExclusaoPendente] = useState<NomeServico[] | null>(null);
  const [termoBusca, setTermoBusca] = useState("");
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [nomes, setNomes] = useState<NomeServico[]>([]);
  const [nomesSelecionados, setNomesSelecionados] = useState<Set<string>>(new Set());
  const [novoNome, setNovoNome] = useState("");
  const [nomeEmEdicao, setNomeEmEdicao] = useState<NomeServico | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const nomesSelecionadosLista = nomes.filter((nome) => nomesSelecionados.has(nome.id));
  const registrosPorPagina = 20;
  const nomesFiltrados = nomes
    .filter((nome) => nome.nome.toLocaleLowerCase().includes(termoBusca.trim().toLocaleLowerCase()))
    .sort((primeiro, segundo) => primeiro.nome.localeCompare(segundo.nome, "pt-BR", { sensitivity: "base" }));
  const totalPaginas = Math.max(1, Math.ceil(nomesFiltrados.length / registrosPorPagina));
  const paginaSegura = Math.min(paginaAtual, totalPaginas);
  const primeiroRegistro = nomesFiltrados.length ? (paginaSegura - 1) * registrosPorPagina : 0;
  const nomesDaPagina = nomesFiltrados.slice(primeiroRegistro, primeiroRegistro + registrosPorPagina);
  const ultimoRegistro = Math.min(primeiroRegistro + nomesDaPagina.length, nomesFiltrados.length);

  async function carregarNomes() {
    setCarregando(true);
    setErro("");
    try {
      const resposta = await apiFetch(`${apiUrl}/catalogo/nomes-servico`);
      if (!resposta.ok) throw new Error("Não foi possível carregar o catálogo.");
      setNomes((await resposta.json()) as NomeServico[]);
    } catch {
      setErro("Não foi possível carregar os nomes de serviço.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => { void carregarNomes(); }, []);

  useEffect(() => {
    setNomesSelecionados((selecionados) => new Set(
      [...selecionados].filter((id) => nomes.some((nome) => nome.id === id)),
    ));
  }, [nomes]);

  useEffect(() => {
    setPaginaAtual(1);
  }, [termoBusca]);

  useEffect(() => {
    if (paginaAtual > totalPaginas) setPaginaAtual(totalPaginas);
  }, [paginaAtual, totalPaginas]);

  useEffect(() => {
    if (!mensagem) return;
    const temporizador = window.setTimeout(() => setMensagem(""), 3000);
    return () => window.clearTimeout(temporizador);
  }, [mensagem]);

  useEffect(() => {
    if (!erro) return;
    const temporizador = window.setTimeout(() => setErro(""), 5000);
    return () => window.clearTimeout(temporizador);
  }, [erro]);

  async function salvarNome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nome = nomeEmEdicao?.nome ?? novoNome;
    if (!nome.trim()) return;
    setSalvando(true);
    setErro("");
    setMensagem("");
    const editando = nomeEmEdicao !== null;
    try {
      const resposta = await apiFetch(
        editando ? `${apiUrl}/catalogo/nomes-servico/${nomeEmEdicao.id}` : `${apiUrl}/catalogo/nomes-servico`,
        { method: editando ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome: nome.trim() }) },
      );
      if (!resposta.ok) {
        if (resposta.status === 409) throw new Error("Esse nome já está cadastrado.");
        throw new Error("Não foi possível salvar o nome.");
      }
      fecharEditor();
      setMensagem(editando ? "Nome atualizado." : "Nome criado.");
      await carregarNomes();
    } catch (error) {
      setErro(error instanceof TypeError ? "Não foi possível conectar à API. Verifique se o backend está em execução." : error instanceof Error ? error.message : "Não foi possível salvar o nome.");
    } finally {
      setSalvando(false);
    }
  }

  function fecharEditor() {
    setEditorOpen(false);
    setNomeEmEdicao(null);
    setNovoNome("");
  }

  function abrirNovoNome() {
    setNomeEmEdicao(null);
    setNovoNome("");
    setEditorOpen(true);
  }

  function abrirEdicao(nome: NomeServico) {
    setNomesSelecionados(new Set([nome.id]));
    setNomeEmEdicao(nome);
    setEditorOpen(true);
  }

  async function removerNome(nomeServico: NomeServico) {
    setExclusaoPendente([nomeServico]);
  }

  async function confirmarExclusao() {
    if (!exclusaoPendente?.length) return;
    setErro("");
    setMensagem("");
    const respostas = await Promise.all(
      exclusaoPendente.map((nome) => apiFetch(`${apiUrl}/catalogo/nomes-servico/${nome.id}`, { method: "DELETE" })),
    );
    const falhou = respostas.find((resposta) => !resposta.ok);
    if (falhou) {
      setErro(falhou.status === 409 ? "Este nome está sendo usado por um serviço e não pode ser removido." : "Não foi possível remover o nome.");
      setExclusaoPendente(null);
      return;
    }
    setNomesSelecionados(new Set());
    setExclusaoPendente(null);
    setMensagem(exclusaoPendente.length === 1 ? "Nome removido." : `${exclusaoPendente.length} nomes removidos.`);
    await carregarNomes();
  }

  function alternarSelecao(nome: NomeServico) {
    setNomesSelecionados((selecionados) => {
      const proximaSelecao = new Set(selecionados);
      if (proximaSelecao.has(nome.id)) {
        proximaSelecao.delete(nome.id);
      } else {
        proximaSelecao.add(nome.id);
      }
      return proximaSelecao;
    });
  }

  function aplicarSelecao(ids: Set<string>) {
    setNomesSelecionados(ids);
    if (ids.size !== 1) {
      fecharEditor();
    }
  }

  function selecionarTodos() {
    aplicarSelecao(new Set(nomes.map((nome) => nome.id)));
  }

  function selecionarNenhum() {
    aplicarSelecao(new Set());
  }

  function inverterSelecao() {
    const invertidos = new Set(
      nomes.filter((nome) => !nomesSelecionados.has(nome.id)).map((nome) => nome.id),
    );
    aplicarSelecao(invertidos);
  }

  async function removerSelecionados() {
    const quantidade = nomesSelecionadosLista.length;
    if (quantidade) setExclusaoPendente(nomesSelecionadosLista);
  }

  function renderEditor() {
    return (
      <form className="catalog-editor catalog-editor-full" onSubmit={salvarNome}>
        <div className="editor-heading">
          <div>
            <p className="eyebrow">{nomeEmEdicao ? "Edição" : "Novo registro"}</p>
            <h4>{nomeEmEdicao ? "Editar nome" : "Adicionar nome"}</h4>
          </div>
          <button className="close-editor" type="button" aria-label="Fechar editor" onClick={fecharEditor}>×</button>
        </div>
        <label>
          <span>Nome do serviço</span>
          <input value={nomeEmEdicao?.nome ?? novoNome} onChange={(event) => nomeEmEdicao ? setNomeEmEdicao({ ...nomeEmEdicao, nome: event.target.value }) : setNovoNome(event.target.value)} placeholder="Ex.: Manicure" required />
        </label>
        <div className="editor-actions">
          <button className="icon-action save-action" type="submit" disabled={salvando} title={nomeEmEdicao ? "Atualizar nome" : "Adicionar nome"} aria-label={nomeEmEdicao ? "Atualizar nome" : "Adicionar nome"}><Save size={17} /></button>
          <button className="icon-action cancel-action" type="button" onClick={fecharEditor} title="Cancelar" aria-label="Cancelar"><X size={17} /></button>
        </div>
      </form>
    );
  }

  function renderPaginacao() {
    if (carregando || !nomesFiltrados.length) return null;
    return (
      <div className="catalog-pagination">
        <span className="catalog-range">{primeiroRegistro + 1}–{ultimoRegistro} de {nomesFiltrados.length}</span>
        <div className="page-buttons">
          <button type="button" disabled={paginaSegura === 1} onClick={() => setPaginaAtual(1)} aria-label="Primeira página" title="Primeira página"><ChevronsLeft size={15} /></button>
          <button type="button" disabled={paginaSegura === 1} onClick={() => setPaginaAtual((pagina) => pagina - 1)} aria-label="Página anterior" title="Página anterior"><ChevronLeft size={15} /></button>
          {Array.from({ length: totalPaginas }, (_, index) => index + 1).map((pagina) => <button className={pagina === paginaSegura ? "page-button active" : "page-button"} type="button" key={pagina} onClick={() => setPaginaAtual(pagina)} aria-current={pagina === paginaSegura ? "page" : undefined}>{pagina}</button>)}
          <button type="button" disabled={paginaSegura === totalPaginas} onClick={() => setPaginaAtual((pagina) => pagina + 1)} aria-label="Próxima página" title="Próxima página"><ChevronRight size={15} /></button>
          <button type="button" disabled={paginaSegura === totalPaginas} onClick={() => setPaginaAtual(totalPaginas)} aria-label="Última página" title="Última página"><ChevronsRight size={15} /></button>
        </div>
      </div>
    );
  }

  const avatarLabel = (userName ?? "Administrador").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");

  return (
    <section className="admin-area" id="administracao" aria-labelledby="admin-title">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-heading">
          <div className="admin-identity">
            <div className="admin-avatar-menu">
              <button className="user-avatar" type="button" aria-label="Abrir menu da conta" aria-expanded={accountMenuOpen} onClick={() => setAccountMenuOpen((open) => !open)}>{avatarLabel}</button>
              {accountMenuOpen && <div className="avatar-popover admin-avatar-popover"><span>{userName}</span><button className="popover-action" type="button" onClick={() => void logout()}>Sair</button></div>}
            </div>
            <p className="eyebrow">Administração</p>
          </div>
          <h2 id="admin-title">Agenda</h2>
        </div>
        <nav className="admin-nav" aria-label="Menu administrativo">
          <button className={section === "overview" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("overview")}>Visão geral</button>
          <p className="admin-nav-label">Catálogos</p>
          <button className={section === "catalog" ? "admin-nav-item active" : "admin-nav-item"} type="button" onClick={() => setSection("catalog")}>Nomes de Serviço</button>
          <button className="admin-nav-item muted" type="button" disabled>Categorias</button>
          <button className="admin-nav-item muted" type="button" disabled>Tipos de procedimento</button>
          <p className="admin-nav-label">Operação</p>
          <button className="admin-nav-item muted" type="button" disabled>Usuários</button>
          <button className="admin-nav-item muted" type="button" disabled>Organizações</button>
          <button className="admin-nav-item muted" type="button" disabled>Permissões</button>
        </nav>
      </aside>
      <div className="admin-content">
        {section === "overview" && <header className="admin-heading">
          <div>
            <p className="eyebrow">Administração da plataforma</p>
            <div className="admin-title-line">
              <h2>Visão geral</h2>
            </div>
            <p className="admin-copy">Acompanhe os recursos centrais da plataforma.</p>
          </div>
          <span className="admin-badge">Administrador</span>
        </header>}
        {section === "overview" && <div className="admin-overview">
          <div className="admin-stat-grid">
            <article className="admin-stat"><span className="admin-stat-label">Nomes de Serviço</span><strong>{carregando ? "-" : nomes.length}</strong><button className="text-button" type="button" onClick={() => setSection("catalog")}>Abrir catálogo</button></article>
            <article className="admin-stat muted-stat"><span className="admin-stat-label">Categorias</span><strong>-</strong><span>Em preparação</span></article>
            <article className="admin-stat muted-stat"><span className="admin-stat-label">Usuários</span><strong>-</strong><span>Em preparação</span></article>
          </div>
          <div className="admin-welcome"><p className="eyebrow">Próximo passo</p><h3>Organize os catálogos da plataforma.</h3><p>Use o menu lateral para manter os dados compartilhados por profissionais e clientes.</p><button type="button" onClick={() => setSection("catalog")}>Gerenciar nomes de serviço</button></div>
        </div>}
        {section === "catalog" && <div className="catalog-panel">
          <div className="catalog-heading"><div><h3>Nomes de Serviço</h3></div><div className="catalog-heading-actions"><span className="result-count">{nomes.length} item{nomes.length === 1 ? "" : "s"}</span><button className={buscaOpen ? "icon-action search-icon active-icon" : "icon-action search-icon"} type="button" title="Buscar nomes de serviço" aria-label="Buscar nomes de serviço" aria-pressed={buscaOpen} onClick={() => setBuscaOpen((open) => !open)}><Search size={19} /></button><button className="icon-action add-icon" type="button" title="Novo nome de serviço" aria-label="Novo nome de serviço" onClick={abrirNovoNome}><Plus size={20} strokeWidth={2} /></button></div></div>
          {!editorOpen && buscaOpen && <div className="catalog-toolbar"><label htmlFor="buscar-nome-servico">Buscar</label><input id="buscar-nome-servico" value={termoBusca} onChange={(event) => setTermoBusca(event.target.value)} placeholder="Filtrar nomes de serviço" autoFocus /><span className="catalog-range">{nomesFiltrados.length ? `${primeiroRegistro + 1}–${ultimoRegistro} de ${nomesFiltrados.length}` : "0 de 0"}</span></div>}
          {!editorOpen && nomesSelecionadosLista.length > 0 && <div className="selection-toolbar"><span>{nomesSelecionadosLista.length} selecionado{nomesSelecionadosLista.length === 1 ? "" : "s"}</span><button className="icon-action subtle" type="button" title="Editar registro selecionado" aria-label="Editar registro selecionado" disabled={nomesSelecionadosLista.length !== 1} onClick={() => { const nome = nomesSelecionadosLista[0]; if (nome) abrirEdicao(nome); }}><Pencil size={16} /></button><button className="icon-action danger-icon" type="button" title="Excluir registros selecionados" aria-label="Excluir registros selecionados" onClick={() => void removerSelecionados()}><Trash2 size={16} /></button></div>}
          {erro && <p className="toast-message error" role="alert">{erro}</p>}
          {mensagem && <p className="toast-message success" role="status">{mensagem}</p>}
          {editorOpen ? renderEditor() : <div className="catalog-workspace">
            <div>
              {carregando && <p className="message">Carregando catálogo...</p>}
              {!carregando && nomes.length === 0 && <p className="message">Nenhum nome de serviço cadastrado.</p>}
              {!carregando && nomesFiltrados.length === 0 && nomes.length > 0 && <p className="message">Nenhum nome corresponde à busca.</p>}
              {renderPaginacao()}
              {!carregando && nomesFiltrados.length > 0 && <div className="catalog-table" role="table" aria-label="Nomes de serviço"><div className="catalog-table-header"><div className="selection-shortcuts"><button type="button" onClick={selecionarTodos}>Todos</button><button type="button" onClick={selecionarNenhum}>Nenhum</button><button type="button" onClick={inverterSelecao}>Inverter seleção</button></div><span>{nomesSelecionadosLista.length ? `${nomesSelecionadosLista.length} selecionado${nomesSelecionadosLista.length === 1 ? "" : "s"}` : ""}</span></div>{nomesDaPagina.map((nome) => <div className={nomesSelecionados.has(nome.id) ? "catalog-row selected" : "catalog-row"} role="row" key={nome.id}><label><input type="checkbox" checked={nomesSelecionados.has(nome.id)} onChange={() => alternarSelecao(nome)} aria-label={`Selecionar ${nome.nome}`} /></label><span role="cell">{nome.nome}</span><div className="row-actions" role="cell"><button className="icon-action subtle" type="button" title="Editar nome de serviço" aria-label="Editar nome de serviço" disabled={nomesSelecionados.size > 1} onClick={() => abrirEdicao(nome)}><Pencil size={15} /></button><button className="icon-action danger-icon" type="button" title="Remover nome de serviço" aria-label="Remover nome de serviço" onClick={() => void removerNome(nome)}><Trash2 size={15} /></button></div></div>)}</div>}
              {renderPaginacao()}
            </div>
          </div>}
        </div>}
      </div>
      {exclusaoPendente && <div className="confirm-backdrop" role="presentation" onClick={() => setExclusaoPendente(null)}>
        <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title" onClick={(event) => event.stopPropagation()}>
          <div className="attention-icon" aria-hidden="true">!</div>
          <div className="confirm-content">
            <h3 id="confirm-title">Confirmar exclusão</h3>
            <p>{exclusaoPendente.length === 1 ? `O nome “${exclusaoPendente[0].nome}” será removido.` : `${exclusaoPendente.length} nomes de serviço serão removidos.`}</p>
            <span>Essa ação não poderá ser desfeita.</span>
          </div>
          <div className="confirm-actions">
            <button className="secondary-button" type="button" onClick={() => setExclusaoPendente(null)}>Cancelar</button>
            <button className="danger-button" type="button" onClick={() => void confirmarExclusao()}>Excluir</button>
          </div>
        </div>
      </div>}
    </section>
  );
}
