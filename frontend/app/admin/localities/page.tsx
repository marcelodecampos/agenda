"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { AppIconButton } from "@/components/ui/app-button";
import { Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, X, Pencil, Trash2, Plus, Search } from "@/components/ui/icons";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "../../auth-provider";

type Kind = "units" | "municipalities";
type Unit = { id: string; ibge_code: string; name: string; abbreviation: string };
type Municipality = { id: string; ibge_code: string; name: string; federative_unit_id: string; federative_unit_name: string; federative_unit_abbreviation: string };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";
const pageSize = 20;

export default function LocalitiesPage() {
  const { authenticated, loading: authLoading, roles, login, apiFetch } = useAuth();
  const [kind, setKind] = useState<Kind>("units");
  const [records, setRecords] = useState<(Unit | Municipality)[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Unit | Municipality | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [abbreviation, setAbbreviation] = useState("");
  const [federativeUnitId, setFederativeUnitId] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const isAdmin = roles.includes("platform_admin");
  const resource = kind === "units" ? "federative-units" : "municipalities";
  const visible = useMemo(() => records.slice((page - 1) * pageSize, page * pageSize), [page, records]);
  const pages = Math.max(1, Math.ceil(records.length / pageSize));

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const response = await apiFetch(`${apiUrl}/admin/${resource}${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`);
      if (!response.ok) throw new Error("Não foi possível carregar a lista.");
      setRecords((await response.json()) as (Unit | Municipality)[]);
    } catch { setError("Não foi possível carregar a lista."); } finally { setLoading(false); }
  }, [apiFetch, resource, search]);

  const loadUnits = useCallback(async () => {
    const response = await apiFetch(`${apiUrl}/admin/federative-units`);
    if (response.ok) setUnits((await response.json()) as Unit[]);
  }, [apiFetch]);

  useEffect(() => { if (authenticated && isAdmin) queueMicrotask(() => void load()); }, [authenticated, isAdmin, load]);
  useEffect(() => { if (authenticated && isAdmin && kind === "municipalities") queueMicrotask(() => void loadUnits()); }, [authenticated, isAdmin, kind, loadUnits]);

  function cancelForm() { setFormOpen(false); setEditing(null); setName(""); setCode(""); setAbbreviation(""); setFederativeUnitId(""); }
  function switchKind(next: Kind) { setKind(next); setPage(1); setSearch(""); setRecords([]); cancelForm(); }
  function startCreate() { setEditing(null); setName(""); setCode(""); setAbbreviation(""); setFederativeUnitId(units[0]?.id ?? ""); setFormOpen(true); }
  function startEdit(record: Unit | Municipality) { setEditing(record); setName(record.name); setCode(record.ibge_code); setAbbreviation("abbreviation" in record ? record.abbreviation : ""); setFederativeUnitId("federative_unit_id" in record ? record.federative_unit_id : ""); setFormOpen(true); }
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); setError(""); const payload = kind === "units" ? { ibge_code: code, name, abbreviation } : { ibge_code: code, name, federative_unit_id: federativeUnitId }; try { const response = await apiFetch(editing ? `${apiUrl}/admin/${resource}/${editing.id}` : `${apiUrl}/admin/${resource}`, { method: editing ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); if (!response.ok) throw new Error("Não foi possível salvar."); cancelForm(); await load(); } catch (saveError) { setError(saveError instanceof Error ? saveError.message : "Não foi possível salvar."); } finally { setSaving(false); } }
  async function remove(record: Unit | Municipality) { if (!window.confirm(`Excluir ${record.name}?`)) return; const response = await apiFetch(`${apiUrl}/admin/${resource}/${record.id}`, { method: "DELETE" }); if (response.ok) await load(); else setError("Não foi possível excluir o registro."); }

  if (authLoading) return <main id="localities-loading" className="admin-loading">Verificando acesso...</main>;
  if (!authenticated) return <main id="localities-login" className="admin-gate"><h1>Entre para continuar.</h1><button id="localities-login-button" type="button" onClick={() => void login()}>Entrar</button></main>;
  if (!isAdmin) return <main id="localities-forbidden" className="admin-gate"><h1>Acesso restrito.</h1></main>;

  const groups = [{ id: "localities-group-tables", label: "Tabelas", items: [{ id: "localities-nav-gender", label: "Gênero", href: "/admin/genders" }, { id: "localities-nav-locality", label: "Localidade", href: "/admin/localities", active: true }] }, { id: "localities-group-people", label: "Pessoa", items: [{ id: "localities-nav-persons", label: "Pessoa física", href: "/admin/people" }, { id: "localities-nav-companies", label: "Pessoa jurídica", href: "/admin/people" }] }, { id: "localities-group-layout", label: "Elementos de layout", items: [{ id: "localities-nav-buttons", label: "Botões", href: "/admin/button-lab" }] }];
  return <main id="localities-admin" className="admin-area"><AdminSidebar id="localities-sidebar" groups={groups} /><section id="localities-content" className="admin-content"><header className="admin-heading"><div><p className="eyebrow">Tabelas</p><div className="admin-title-line"><h1 className="admin-page-title">Localidade</h1><span className="admin-badge">Administrador</span></div></div></header><div id="localities-tabs" className="organization-tabs"><button id="localities-units-tab" className={kind === "units" ? "organization-tab active" : "organization-tab"} type="button" onClick={() => switchKind("units")}>Unidades federativas</button><button id="localities-municipalities-tab" className={kind === "municipalities" ? "organization-tab active" : "organization-tab"} type="button" onClick={() => switchKind("municipalities")}>Municípios</button></div>{formOpen ? <form id="locality-form" className="gender-editor-screen" onSubmit={save}><label htmlFor="locality-name"><span>Nome</span><input id="locality-name" required value={name} onChange={(event) => setName(event.target.value)} /></label><label htmlFor="locality-code"><span>Código IBGE</span><input id="locality-code" required value={code} onChange={(event) => setCode(event.target.value)} /></label>{kind === "units" ? <label htmlFor="locality-abbreviation"><span>Sigla</span><input id="locality-abbreviation" required value={abbreviation} onChange={(event) => setAbbreviation(event.target.value)} /></label> : <label htmlFor="locality-federative-unit"><span>Unidade federativa</span><select id="locality-federative-unit" required value={federativeUnitId} onChange={(event) => setFederativeUnitId(event.target.value)}><option value="">Selecione</option>{units.map((unit) => <option id={`locality-unit-option-${unit.id}`} key={unit.id} value={unit.id}>{unit.name} ({unit.abbreviation})</option>)}</select></label>}<div className="editor-actions"><AppIconButton id="locality-save" type="submit" variant="success" size="icon" disabled={saving} title="Salvar" aria-label="Salvar"><Check /></AppIconButton><AppIconButton id="locality-cancel" type="button" variant="danger" size="icon" onClick={cancelForm} title="Cancelar" aria-label="Cancelar"><X /></AppIconButton></div></form> : <><div className="catalog-heading"><div className="catalog-heading-actions"><AppIconButton id="locality-add" className="icon-action add-icon" type="button" variant="outline" size="icon" onClick={startCreate} title="Adicionar" aria-label="Adicionar"><Plus /></AppIconButton><AppIconButton id="locality-search-toggle" className="icon-action search-icon" type="button" variant="outline" size="icon" title="Pesquisar" aria-label="Pesquisar"><Search /></AppIconButton></div></div><div className="catalog-toolbar"><label htmlFor="locality-search">Pesquisar</label><input id="locality-search" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Nome ou código" /></div>{error && <p id="localities-error" className="message error" role="alert">{error}</p>}{loading && <p id="localities-loading-records" className="message">Carregando...</p>}{!loading && <><div id="localities-pagination-top" className="catalog-pagination"><span className="catalog-range">Página {page} de {pages}</span><div className="page-buttons"><button id="localities-first-page" type="button" onClick={() => setPage(1)} disabled={page === 1}><ChevronsLeft /></button><button id="localities-previous-page" type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page === 1}><ChevronLeft /></button><button id="localities-next-page" type="button" onClick={() => setPage((current) => Math.min(pages, current + 1))} disabled={page === pages}><ChevronRight /></button><button id="localities-last-page" type="button" onClick={() => setPage(pages)} disabled={page === pages}><ChevronsRight /></button></div></div><Table id="localities-table" className="gender-data-table"><TableHeader id="localities-table-header"><TableRow id="localities-header-row"><TableHead id="localities-name-header">Nome</TableHead><TableHead id="localities-code-header">Código IBGE</TableHead><TableHead id="localities-extra-header">{kind === "units" ? "Sigla" : "UF"}</TableHead><TableHead id="localities-actions-header" className="gender-action-column">Ações</TableHead></TableRow></TableHeader><TableBody id="localities-table-body">{visible.map((record) => <TableRow id={`locality-row-${record.id}`} key={record.id}><TableCell id={`locality-name-${record.id}`}>{record.name}</TableCell><TableCell id={`locality-code-${record.id}`}>{record.ibge_code}</TableCell><TableCell id={`locality-extra-${record.id}`}>{"abbreviation" in record ? record.abbreviation : `${record.federative_unit_name} (${record.federative_unit_abbreviation})`}</TableCell><TableCell id={`locality-actions-${record.id}`} className="gender-action-column"><AppIconButton id={`locality-edit-${record.id}`} type="button" variant="ghost" size="icon" onClick={() => startEdit(record)} title="Editar" aria-label={`Editar ${record.name}`}><Pencil /></AppIconButton><AppIconButton id={`locality-delete-${record.id}`} type="button" variant="danger" size="icon" onClick={() => void remove(record)} title="Excluir" aria-label={`Excluir ${record.name}`}><Trash2 /></AppIconButton></TableCell></TableRow>)}</TableBody></Table><div id="localities-pagination-bottom" className="catalog-pagination"><span className="catalog-range">Página {page} de {pages}</span></div></>}</> }</section></main>;
}
